"""Index the library with the FULL model (text + vision + audio). Run once, then again when files change.

- Photos: one vector each.
- Audio: overlapping 30 s windows, so a search can jump to the moment that matches.
- Video: the picture (frames at 1 per second, 30 s windows) and the soundtrack (30 s windows) are indexed
  separately, so you can find a video by what you see or by what you hear in it.
- Documents (library/docs): every PDF page as a picture (so scans, charts and maps work) plus its text in
  ~200-word pieces; scanned photos of text as a picture. PDF tools: poppler (pdftoppm, pdftotext, pdfinfo).

Only new or changed files are embedded; everything else is reused from the last run.
Writes library_index.npy + library_index.json next to the library folder.

Run: python app/indexer.py
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HOME", "D:/hf-cache")

import numpy as np

ROOT = Path(os.environ.get("WORKSPACE") or Path(__file__).resolve().parent.parent).resolve()   # WORKSPACE: another folder with its own library/
LIB = ROOT / "library"
CHUNKS = ROOT / ".cache" / "chunks"
INDEX_NPY = ROOT / "library_index.npy"
INDEX_JSON = ROOT / "library_index.json"

KINDS = {
    "image": {".jpg", ".jpeg", ".png", ".webp"},
    "audio": {".mp3", ".wav", ".ogg", ".oga", ".m4a", ".flac"},
    "video": {".mp4", ".webm", ".mov", ".mkv"},
}
WINDOW, HOP = 30, 20          # audio windows: 30 s long, a new one every 20 s
VIDEO_WINDOW = 30             # video picture windows: 30 frames at 1 fps (30 x 140 = 4,200 tokens)
FRAME = 448


def kind_of(p: Path):
    if p.parent.name == "docs" and p.suffix.lower() in KINDS["image"] | {".pdf"}:
        return "doc"
    return next((k for k, exts in KINDS.items() if p.suffix.lower() in exts), None)


def duration(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def has_audio(p: Path) -> bool:
    return bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip())


def windows(total: float, size: float, hop: float):
    starts = list(np.arange(0, max(total - size, 0) + 1e-6, hop)) or [0.0]
    if starts[-1] + size < total - 1:          # make sure the end is covered
        starts.append(max(total - size, 0))
    return [(round(float(s), 2), round(min(float(s) + size, total), 2)) for s in starts]


def audio_chunk(p: Path, start: float, end: float) -> str:
    out = CHUNKS / f"{p.stem}@{start:.0f}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(end - start), "-i", str(p),
                    "-vn", "-ac", "1", "-ar", "16000", str(out)], check=True)
    return str(out)


def video_frames(p: Path, start: float, end: float) -> np.ndarray:
    vf = f"fps=1,scale={FRAME}:{FRAME}:force_original_aspect_ratio=decrease,pad={FRAME}:{FRAME}:(ow-iw)/2:(oh-ih)/2"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(end - start), "-i", str(p),
                          "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, FRAME, FRAME, 3)


def pdf_pages(p: Path) -> int:
    out = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True).stdout
    return int(next((l.split()[-1] for l in out.splitlines() if l.startswith("Pages:")), "0"))


def page_image(p: Path, page: int) -> str:
    out = CHUNKS / f"{p.stem}-p{page}"
    subprocess.run(["pdftoppm", "-r", "110", "-f", str(page), "-l", str(page), "-png", "-singlefile", str(p), str(out)], check=True)
    return str(out) + ".png"


def page_text_pieces(p: Path, page: int, size: int = 200, overlap: int = 40) -> list:
    words = subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), str(p), "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.split()
    if len(words) < 15:   # a scan without a text layer: the page picture covers it
        return []
    return [" ".join(words[i:i + size]) for i in range(0, max(len(words) - overlap, 1), size - overlap)]


def plan(p: Path, kind: str):
    """The pieces of one file to embed: (row metadata, model input factory, prompt name)."""
    rel = p.relative_to(LIB).as_posix()
    if kind == "image":
        return [({"file": rel, "kind": "image", "part": "picture", "start": 0, "end": 0}, lambda: {"image": str(p)}, None)]
    if kind == "doc":
        if p.suffix.lower() != ".pdf":
            return [({"file": rel, "kind": "doc", "part": "page", "page": 1, "start": 0, "end": 0},
                     lambda: {"image": str(p)}, None)]
        pieces = []
        for page in range(1, pdf_pages(p) + 1):
            pieces.append(({"file": rel, "kind": "doc", "part": "page", "page": page, "start": 0, "end": 0},
                           lambda page=page: {"image": page_image(p, page)}, None))
            for text in page_text_pieces(p, page):
                pieces.append(({"file": rel, "kind": "doc", "part": "text", "page": page, "start": 0, "end": 0},
                               lambda text=text: text, "Document"))
        return pieces
    total = duration(p)
    pieces = []
    if kind == "video":
        for s, e in windows(total, VIDEO_WINDOW, VIDEO_WINDOW):
            pieces.append(({"file": rel, "kind": "video", "part": "picture", "start": s, "end": e},
                           lambda s=s, e=e: {"video": video_frames(p, s, e)}, None))
        if not has_audio(p):
            return pieces
    for s, e in windows(total, WINDOW, HOP):
        pieces.append(({"file": rel, "kind": kind, "part": "sound", "start": s, "end": e},
                       lambda s=s, e=e: {"audio": audio_chunk(p, s, e)}, None))
    return pieces


def main():
    CHUNKS.mkdir(parents=True, exist_ok=True)
    old = json.loads(INDEX_JSON.read_text(encoding="utf-8")) if INDEX_JSON.exists() else {"files": {}, "rows": []}
    old_vecs = np.load(INDEX_NPY) if INDEX_NPY.exists() and old["rows"] else np.zeros((0, 768), np.float32)

    files = sorted(p for p in LIB.rglob("*") if p.is_file() and kind_of(p))
    keep_rows, keep_vecs, todo = [], [], []
    for p in files:
        rel, mtime = p.relative_to(LIB).as_posix(), int(p.stat().st_mtime)
        if old["files"].get(rel) == mtime:
            idx = [i for i, r in enumerate(old["rows"]) if r["file"] == rel]
            keep_rows += [old["rows"][i] for i in idx]
            keep_vecs += [old_vecs[i] for i in idx]
        else:
            todo.append(p)
    print(f"PROGRESS 0/{len(todo)} {len(files)} files, {len(todo)} new or changed", flush=True)

    new_rows, new_vecs = [], []
    if todo:
        import torch
        from sentence_transformers import SentenceTransformer
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.bfloat16 if device == "cuda" and torch.cuda.is_bf16_supported() else torch.float32  # never float16
        model = SentenceTransformer("google/embeddinggemma-2", device=device, model_kwargs={"torch_dtype": dtype})
        t0 = time.time()
        for n, p in enumerate(todo, 1):
            for row, make, prompt in plan(p, kind_of(p)):
                new_vecs.append(model.encode([make()], prompt_name=prompt, normalize_embeddings=True)[0].astype(np.float32))
                new_rows.append(row)
            print(f"PROGRESS {n}/{len(todo)} {p.relative_to(LIB).as_posix()}", flush=True)
        print(f"embedded {len(new_rows)} pieces in {time.time() - t0:.0f}s on {device}", flush=True)

    rows = keep_rows + new_rows
    vecs = np.array(keep_vecs + new_vecs, np.float32).reshape(-1, 768)
    np.save(INDEX_NPY, vecs)
    INDEX_JSON.write_text(json.dumps({
        "files": {p.relative_to(LIB).as_posix(): int(p.stat().st_mtime) for p in files},
        "rows": rows}, indent=0), encoding="utf-8")
    for f in [*CHUNKS.glob("*.wav"), *CHUNKS.glob("*.png")]:
        f.unlink()
    print(f"DONE {len(files)} files, {len(rows)} vectors", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAILED {type(e).__name__}: {e}", flush=True)
        sys.exit(1)
