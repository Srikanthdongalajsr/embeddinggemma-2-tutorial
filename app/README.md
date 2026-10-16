# Search Anything (EmbeddingGemma 2 demo)

Search your photos, audio, videos and PDFs by typing what you're looking for. Everything runs on your own machine.

- **Index once, with the full model:** `indexer.py` turns every file into vectors (text, image and audio parts).
- **Search with the small model:** `server.py` uses only the 270M text part, so searches are fast and need little memory.

This is demo code for a YouTube video, kept short on purpose.

## Setup

Needs Python 3.10+, plus `ffmpeg` and `poppler` (`pdftoppm`, `pdftotext`) on your PATH.

```
pip install torch sentence-transformers numpy
```

Tested with sentence-transformers 6.1 and torch 2.14. A GPU helps for indexing but isn't required.

## Run it (starter library)

```
python app/get_library.py   # download about 90 MB of open-licensed photos, audio, video and PDFs
python app/indexer.py       # build the search index (a few minutes)
python app/server.py        # open http://127.0.0.1:7860
```

On Windows you can double-click `run.bat` for the last step (it uses the GPU; change it to `set DEVICE=cpu` if you don't have one).

Type a search and press Enter. Audio and video results jump to the matching moment. You can drag your own files onto the page to add them.

## Run it (plant library)

A second library for a factory example: type a machine symptom and find the manual page, photo, sound or video.

```
python app/get_plant.py
set WORKSPACE=plant         # macOS/Linux: export WORKSPACE=plant
python app/indexer.py
python app/server.py
```

On Windows, `run_plant.bat` does the last two settings for you.

## Files

| File | What it does |
|---|---|
| `get_library.py`, `get_plant.py` | download the two libraries |
| `indexer.py` | builds the index with the full model |
| `server.py`, `index.html` | the search page |
| `eval.py`, `plant_eval.py`, `plant_hard_eval.py` | test queries that check the right file comes first |
| `walkthrough.py` | the whole idea in about 60 lines (also in `walkthrough.ipynb`) |

## Credits

All media comes from Wikimedia Commons and other public sources (public domain or Creative Commons). Author, licence and source for each file are in `library/CREDITS.json` and `plant/library/CREDITS.json`.
