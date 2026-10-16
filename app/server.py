"""Search your photos, audio and videos by describing them. One page, EmbeddingGemma 2.

Index big, search small:
- indexer.py embeds the library once with the full model (text + vision + audio), in the background.
- This server answers searches with only the 270M text model, comparing the query with those stored vectors.

Run:  python app/server.py   then open http://127.0.0.1:7860
Env:  DEVICE=cpu|cuda (default cpu, search needs no GPU), PORT=7860, OPEN=0 to skip opening the browser
No extra packages: Python's built-in web server.
"""
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

os.environ.setdefault("HF_HOME", "D:/hf-cache")

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

APP = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("WORKSPACE") or APP.parent).resolve()   # WORKSPACE: another folder with its own library/ (e.g. plant/)
LIB = ROOT / "library"
INDEX_NPY = ROOT / "library_index.npy"
INDEX_JSON = ROOT / "library_index.json"
DEVICE = os.environ.get("DEVICE", "cpu")
PORT = int(os.environ.get("PORT", "7860"))
UPLOAD_DIRS = {"image": "images", "audio": "audio", "video": "video", "doc": "docs"}
EXTS = {"image": {".jpg", ".jpeg", ".png", ".webp"}, "audio": {".mp3", ".wav", ".ogg", ".oga", ".m4a", ".flac"},
        "video": {".mp4", ".webm", ".mov", ".mkv"}, "doc": {".pdf"}}

print(f"loading text-only model on {DEVICE} ...", flush=True)
model = SentenceTransformer(
    "google/embeddinggemma-2",
    device=DEVICE,
    model_kwargs={"torch_dtype": torch.bfloat16 if DEVICE == "cuda" else torch.float32},
    config_kwargs={"vision_config": None, "audio_config": None},
)
PARAMS = f"{sum(p.numel() for p in model.parameters()) / 1e6:.0f}M"
for w in ("warm up", "a dog barking in the park", "waves on a beach at sunset"):
    model.encode(w, prompt_name="SearchQuery")  # so the first search on camera isn't the slow one

state = {"rows": [], "vecs": np.zeros((0, 768), np.float32), "credits": {}}
job = {"running": False, "done": 0, "total": 0, "file": "", "message": ""}
peaks_cache = {}


def load_index():
    if INDEX_JSON.exists() and INDEX_NPY.exists():
        state["rows"] = json.loads(INDEX_JSON.read_text(encoding="utf-8"))["rows"]
        state["vecs"] = np.load(INDEX_NPY)
    credits = LIB / "CREDITS.json"
    state["credits"] = json.loads(credits.read_text(encoding="utf-8")) if credits.exists() else {}
    print(f"index: {len({r['file'] for r in state['rows']})} files, {len(state['rows'])} vectors", flush=True)


def pretty(rel: str) -> str:
    return Path(rel).stem.replace("_", " ").replace("-", " ").strip().capitalize()


def view(row: dict, score: float) -> dict:
    return {"file": row["file"], "kind": row["kind"], "part": row["part"], "start": row["start"], "end": row["end"],
            "page": row.get("page", 0), "score": round(score, 3),
            "name": state["credits"].get(row["file"], {}).get("title") or pretty(row["file"]), "src": "/media/" + row["file"]}


def search(query: str, k: int = 9, dim: int = 768, each: bool = False) -> dict:
    t0 = time.perf_counter()
    rows, vecs = state["rows"], state["vecs"]
    if not rows:
        return {"results": [], "ms": 0}
    q = model.encode(query, prompt_name="SearchQuery").astype(np.float32)[:dim]
    docs = vecs[:, :dim]
    # Matryoshka: re-normalise after cutting, then cosine = dot product
    scores = (docs / np.linalg.norm(docs, axis=1, keepdims=True)) @ (q / np.linalg.norm(q))
    best = {}  # one result per file: its best-matching piece (that's where playback starts)
    for i in np.argsort(-scores):
        best.setdefault(rows[i]["file"], int(i))
    order = sorted(best.values(), key=lambda i: -scores[i])
    if each:  # best photo, audio, video and document, so every kind gets a slot
        order = [next(i for i in order if rows[i]["kind"] == kd) for kd in ("image", "audio", "video", "doc")
                 if any(rows[i]["kind"] == kd for i in order)]
    ms = (time.perf_counter() - t0) * 1000
    return {"results": [view(rows[i], float(scores[i])) for i in order[:k]],
            "ms": round(ms), "dim": dim, "device": DEVICE.upper(), "params": PARAMS}


def library() -> list:
    seen = {}
    for r in state["rows"]:
        seen.setdefault(r["file"], view(r, 0.0))
    return sorted(seen.values(), key=lambda v: ("image", "video", "doc", "audio").index(v["kind"]))


def peaks(rel: str, n: int = 120) -> list:
    """Loudness outline of an audio file for the waveform, computed once."""
    if rel not in peaks_cache:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(LIB / rel), "-vn", "-ac", "1", "-ar", "4000",
                              "-f", "f32le", "-"], capture_output=True).stdout
        x = np.abs(np.frombuffer(raw, np.float32))
        chunks = np.array_split(x, n) if len(x) >= n else [x]
        p = np.array([c.max() if len(c) else 0 for c in chunks])
        peaks_cache[rel] = (p / (p.max() or 1)).round(3).tolist()
    return peaks_cache[rel]


THUMBS = ROOT / ".cache" / "thumbs"


def thumb(rel: str, t: float) -> bytes:
    """A still frame of a video at the matched moment (shown before the video loads)."""
    THUMBS.mkdir(parents=True, exist_ok=True)
    out = THUMBS / f"{Path(rel).stem}@{t:.1f}.jpg"
    if not out.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(LIB / rel), "-frames:v", "1",
                        "-vf", "scale=640:-2", "-q:v", "4", str(out)], check=False)
    return out.read_bytes() if out.exists() else b""


def page_png(rel: str, page: int, res: int = 60) -> bytes:
    """A document page as a picture: PDFs are rendered, scans are served as they are."""
    f = LIB / rel
    if f.suffix.lower() != ".pdf":
        return f.read_bytes()
    THUMBS.mkdir(parents=True, exist_ok=True)
    out = THUMBS / f"{f.stem}-p{page}-r{res}"
    if not Path(str(out) + ".png").exists():
        subprocess.run(["pdftoppm", "-r", str(res), "-f", str(page), "-l", str(page), "-png", "-singlefile",
                        str(f), str(out)], check=False)
    png = Path(str(out) + ".png")
    return png.read_bytes() if png.exists() else b""


def run_indexer():
    """Index new files with the full model in a separate process, then reload."""
    job.update(running=True, done=0, total=0, file="", message="Starting the full model...")
    proc = subprocess.Popen([sys.executable, "-u", str(APP / "indexer.py")], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    for line in proc.stdout:
        m = re.match(r"PROGRESS (\d+)/(\d+) (.*)", line.strip())
        if m:
            job.update(done=int(m[1]), total=int(m[2]), file=m[3], message="")
        elif line.startswith(("DONE", "FAILED")):
            job["message"] = line.strip()
    proc.wait()
    load_index()
    job["running"] = False


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, ctype: str, code: int = 200, extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        self._send(json.dumps(obj).encode(), "application/json")

    def _media(self, path: Path):
        # Range support, so the browser can jump to the matched moment in audio and video
        size = path.stat().st_size
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if not m:
            return self._send(path.read_bytes(), ctype, extra={"Accept-Ranges": "bytes"})
        start = int(m[1]) if m[1] else size - int(m[2])
        end = min(int(m[2]) if m[1] and m[2] else size - 1, size - 1)
        end = min(end, start + 2 * 1024 * 1024 - 1)  # 2 MB at a time, so many players don't block each other
        with open(path, "rb") as f:
            f.seek(start)
            body = f.read(end - start + 1)
        self._send(body, ctype, 206, {"Accept-Ranges": "bytes", "Content-Range": f"bytes {start}-{end}/{size}"})

    def do_GET(self):
        url = urlparse(self.path)
        p = parse_qs(url.query)
        if url.path == "/":
            return self._send((APP / "index.html").read_bytes(), "text/html; charset=utf-8")
        if url.path == "/api/library":
            return self._json({"results": library()})
        if url.path == "/api/search":
            q = p.get("q", [""])[0].strip()
            if not q:
                return self._json({"results": []})
            return self._json(search(q, int(p.get("k", ["9"])[0]), int(p.get("dim", ["768"])[0]),
                                     p.get("each", ["0"])[0] == "1"))
        if url.path == "/api/peaks":
            return self._json(peaks(p.get("f", [""])[0]))
        if url.path == "/api/thumb":
            return self._send(thumb(p.get("f", [""])[0], float(p.get("t", ["0"])[0])), "image/jpeg",
                              extra={"Cache-Control": "max-age=86400"})
        if url.path == "/api/page":
            rel = p.get("f", [""])[0]
            res = min(max(int(p.get("r", ["60"])[0]), 40), 150)  # small for tiles, sharper for the pop-up view
            body = page_png(rel, int(p.get("p", ["1"])[0]), res)
            ctype = "image/png" if rel.lower().endswith(".pdf") else (mimetypes.guess_type(rel)[0] or "image/jpeg")
            return self._send(body, ctype, extra={"Cache-Control": "max-age=86400"})
        if url.path == "/api/status":
            return self._json(job)
        if url.path == "/api/credits":
            return self._json(state["credits"])
        if url.path.startswith("/media/"):
            f = (LIB / unquote(url.path[len("/media/"):])).resolve()
            if LIB.resolve() in f.parents and f.is_file():
                return self._media(f)
        self._send(b"not found", "text/plain", 404)

    def do_POST(self):
        url = urlparse(self.path)
        if url.path == "/api/rescan":
            if not job["running"]:
                threading.Thread(target=run_indexer, daemon=True).start()
            return self._json({"started": True})
        if url.path == "/api/record":
            # a voice note recorded in the page (webm/ogg opus): save as mp3, give it a readable title, index it
            data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            now = time.localtime()
            rel = f"audio/voice_note_{time.strftime('%Y%m%d_%H%M%S', now)}.mp3"
            proc = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "pipe:0", "-vn", "-ac", "1", "-b:a", "96k",
                                   str(LIB / rel)], input=data, capture_output=True)
            if proc.returncode:
                return self._send(proc.stderr or b"could not read the recording", "text/plain", 400)
            state["credits"][rel] = {"title": time.strftime("Voice note, %d %b %H:%M", now),
                                     "author": "Recorded in the app", "license": "Own recording", "source": ""}
            (LIB / "CREDITS.json").write_text(json.dumps(state["credits"], indent=1, ensure_ascii=False), encoding="utf-8")
            if not job["running"]:
                job["running"] = True          # set before the thread starts, so the page's first poll sees it
                threading.Thread(target=run_indexer, daemon=True).start()
            return self._json({"saved": rel})
        if url.path == "/api/upload":
            name = Path(unquote(self.headers.get("X-Filename", ""))).name
            kind = next((k for k, e in EXTS.items() if Path(name).suffix.lower() in e), None)
            if not name or not kind:
                return self._send(b"unsupported file type", "text/plain", 400)
            data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            (LIB / UPLOAD_DIRS[kind] / name).write_bytes(data)
            return self._json({"saved": f"{UPLOAD_DIRS[kind]}/{name}"})
        self._send(b"not found", "text/plain", 404)

    def log_message(self, *args):
        pass


load_index()

if __name__ == "__main__":
    print(f"open http://127.0.0.1:{PORT}", flush=True)
    if os.environ.get("OPEN", "1") == "1":
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
