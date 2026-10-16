"""Download a small, free sample 'phone library': ESC-50 sound clips + COCO photos."""
import csv, io, json, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent / "data"
(ROOT / "audio").mkdir(parents=True, exist_ok=True)
(ROOT / "images").mkdir(parents=True, exist_ok=True)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "embeddinggemma2-demo"})
    return urllib.request.urlopen(req, timeout=60).read()

# --- Audio: one 5-second clip per category from ESC-50 (CC BY-NC 3.0) ---
ESC = "https://raw.githubusercontent.com/karolpiczak/ESC-50/master/"
WANT = ["dog", "rain", "sea_waves", "crying_baby", "church_bells",
        "siren", "rooster", "keyboard_typing", "train", "clock_tick"]
rows = list(csv.DictReader(io.StringIO(fetch(ESC + "meta/esc50.csv").decode())))
for cat in WANT:
    row = next(r for r in rows if r["category"] == cat)
    out = ROOT / "audio" / f"{cat}.wav"
    if not out.exists():
        out.write_bytes(fetch(ESC + "audio/" + row["filename"]))
    print("audio", cat, row["filename"])

# --- Photos: Wikimedia Commons (free licences, resized to 640px wide) ---
WIKI = "https://commons.wikimedia.org/wiki/Special:FilePath/{}?width=640"
PHOTOS = {
    "labrador": "YellowLabradorLooking_new.jpg",
    "cat": "Cat03.jpg",
    "sunset": "Sunset_2007-1.jpg",
    "golden_gate": "Golden_Gate_Bridge_as_seen_from_Battery_East.jpg",
    "apple": "Red_Apple.jpg",
    "pizza": "Pizza-3007395.jpg",
    "everest": "Mount_Everest_as_seen_from_Drukair2_PLW_edit.jpg",
    "rooster": "Rooster_portrait2.jpg",
    "horses": "Biandintz_eta_zaldiak_-_modified2.jpg",
    "big_ben": "Big_Ben_2007-1.jpg",
    "baby": "Baby_Face.JPG",
    "beach": "RK_Beach_Visakhapatnam_Nov_2012_-_02.JPG",
}
for name, f in PHOTOS.items():
    out = ROOT / "images" / f"{name}.jpg"
    if not out.exists():
        out.write_bytes(fetch(WIKI.format(f)))
    print("image", name, f)
json.dump({"audio": "ESC-50 (CC BY-NC 3.0), github.com/karolpiczak/ESC-50",
           "images": {k: "https://commons.wikimedia.org/wiki/File:" + v for k, v in PHOTOS.items()}},
          open(ROOT / "SOURCES.json", "w"), indent=2)
