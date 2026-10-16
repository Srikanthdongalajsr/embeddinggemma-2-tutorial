"""Download the starter library: real photos, speeches, songs and videos from Wikimedia Commons.

Everything is openly licensed (public domain or Creative Commons); credits go to library/CREDITS.json.
Photos are saved at 800 px (phone-photo size, not HD), audio trimmed to the part we use, videos re-encoded to 480p.
Your own files can go into the same library/ folders; the indexer picks up anything it finds there.

Run: python app/get_library.py   (needs ffmpeg on PATH)
"""
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "library"
CACHE = ROOT / ".cache" / "downloads"
UA = {"User-Agent": "EG2SearchDemo/1.0 (local research demo; contact common.ai@atliq.com)"}

IMAGES = {
    "park_town_signal_chennai": "Park Town signal.JPG",
    "lime_soda_cart": "Lime soda (46693944265).jpg",
    "colour_powders_kochi": "Jew Street Mattancherry, Fort Kochi, Ernakulam, Kerala, India IMG 20190526 145550.jpg",
    "jew_street_kochi": "Jew Street Mattancherry, Fort Kochi, Ernakulam, Kerala, India IMG 20190526 150110.jpg",
    "triplicane_high_road": "Triplicane High Road (244391773).jpeg",
    "koottanad_street": "Street view of Koottanad town, Palakkad, Kerala, India.jpg",
    "pune_traffic_signal": "Pune Busy trafic at Signal on Nagar Road.jpg",
    "mumbai_station_rush": "Mumbai morning rush.jpg",
    "street_cricket_mountains": "Street Cricket in India.jpg",
    "kitchen_cooking": "People Cooking in the Kitchen 11.jpg",
    "hyderabad_autos": "Hyderabad City streets traffic View AutoRikshwaws 2005.jpg",
    "bus_stop_hyderabad": "Waiting for bus at a bus stop in Hyderabad.jpg",
    "classroom": "Classroom in India.jpg",
    "coding_class_bangalore": "Students at a school in Bangalore, India learning to code on Progate.jpg",
    "kolkata_street_food_taxi": "Street food & the iconic yellow taxi, Kolkata.jpg",
    "crowded_beach": "Colourful Crowd (6784410498).jpg",
    "cricket_crawford_market": "Cricket by the side of Crawford Market 02.jpg",
    "dinner_table_1971": "Thanksgiving Dinner Table, Broward County Florida, 1971 02.jpg",
}

# key: (Commons title, start seconds, duration seconds or None for the whole file)
AUDIO = {
    "nehru_tryst_with_destiny": ("Tryst with Destiny- Speech by Pt. Jawaharlal Nehru.ogg", 0, None),
    "gandhi_spiritual_message": ("M. K. Gandhi's spiritual message.oga", 0, None),
    "jfk_rice_moon_speech": ("Jfk rice university we choose to go to the moon.ogg", 0, None),
    "fdr_fear_itself": ("First Inauguration of FDR - Fear Itself Excerpt.ogg", 0, None),
    "armstrong_small_step": ("Armstrong Small Step.ogg", 0, None),
    "nasa_podcast_artemis": ("NASA podcast Episode 180 Artemis Mission Management.mp3", 0, 180),
    "jana_gana_mana_1942": ("Jana Gana Mana 1942 performance with introduction.mp3", 0, None),
    "vande_mataram_vaze": ("Vande Mataram by Pt. Chandrashekhar Vaze.ogg", 0, 120),
    "sitar_raga_yaman": ("Sitar sample yaman.ogg", 0, None),
    "moonlight_sonata_allegretto": ("Moonlight Sonata Allegretto.ogg", 0, None),
    "carefree_macleod": ("Kevin MacLeod - Carefree.ogg", 0, 120),
    "windswept_macleod": ("Kevin MacLeod - Windswept.ogg", 0, 120),
}

VIDEO = {
    "hyderabad_traffic": ("Traffic in Hyderabad.webm", 0, None),
    "jalebi_bangalore": ("Jalebi being prepared, Bangalore.webm", 0, None),
    "obbattu_bakery": ('Man preparing "Obbattu" in a bakery in VV Puram, Bengaluru, India.webm', 0, None),
    "stray_cattle_delhi": ("Stray Cattle in Lutyens Delhi.webm", 0, None),
    "heavy_rain_street": ("Heavy rain in Boulevard Rosemont, Montreal.webm", 0, None),
    "cricket_cover_drives": ("Aythorpe Roding CC v Terling CC, Essex, England Video 2 batsman hits cover drives.webm", 0, None),
    "shivajinagar_bus_station": ("Shivaji Nagar Bus Station Bangalore - St. Marys Basilica - Cubbon Park.webm", 0, 120),
    "nasa_west_antarctic": ("West Antarctic Collapse.ogv", 0, None),
}

# Documents go to library/docs. PDFs: (Commons title, how many first pages to keep, or a list of pages). Scans: photos of text, 1200 px.
DOCS = {
    "constitution_preamble": ("THE CONSTITUTION OF INDIA PREAMBLE.pdf", 2),
    "gandhi_letter_to_roosevelt": ("Letter from M. K. Gandhi to President Franklin D. Roosevelt and Reply - DPLA - 6eb5c516503dcd0a74ccbe9d88d7321c.pdf", 4),
    "antoines_menu_1920s": ("Antoine's Restaurant Menu New Orleans 1920s.pdf", 4),
    "india_monsoon_floods_2018": ("ECDM 20180921 India Monsoon Floods.pdf", 2),
    "mars_pathfinder_press_kit": ("NASA Mars Pathfinde Press kit 1997.pdf", [1, 5, 6, 7, 9]),  # cover, story, quick facts
}
SCANS = {
    "hindustan_times_15_aug_1947": "The Hindustan Times front page 15 August 1947 (1187 × 1600).jpg",
    "food_receipt": "Wikipedia Receipt For Food.jpg",
    "pound_cake_recipe_card": "Pound cake recipe card - Handwritten 2024-05-21 103943 page 1.jpg",
}

TITLES = {
    "images/park_town_signal_chennai.jpg": "Park Town signal, Chennai",
    "images/lime_soda_cart.jpg": "Lime soda cart",
    "images/colour_powders_kochi.jpg": "Colour powders, Fort Kochi",
    "images/jew_street_kochi.jpg": "Jew Street, Fort Kochi",
    "images/triplicane_high_road.jpg": "Triplicane High Road, Chennai",
    "images/koottanad_street.jpg": "Koottanad town, Kerala",
    "images/pune_traffic_signal.jpg": "Traffic signal, Pune",
    "images/mumbai_station_rush.jpg": "Morning rush, Mumbai",
    "images/street_cricket_mountains.jpg": "Street cricket in the hills",
    "images/kitchen_cooking.jpg": "Cooking at home",
    "images/hyderabad_autos.jpg": "Autos in Hyderabad",
    "images/bus_stop_hyderabad.jpg": "Bus stop, Hyderabad",
    "images/classroom.jpg": "Classroom",
    "images/coding_class_bangalore.jpg": "Coding class, Bangalore",
    "images/kolkata_street_food_taxi.jpg": "Street food and a yellow taxi, Kolkata",
    "images/crowded_beach.jpg": "Crowded beach",
    "images/cricket_crawford_market.jpg": "Cricket by Crawford Market, Mumbai",
    "images/dinner_table_1971.jpg": "Family dinner, 1971",
    "audio/nehru_tryst_with_destiny.mp3": "Tryst with Destiny, Nehru (1947)",
    "audio/gandhi_spiritual_message.mp3": "Spiritual message, Gandhi (1931)",
    "audio/jfk_rice_moon_speech.mp3": "We choose to go to the Moon, JFK (1962)",
    "audio/fdr_fear_itself.mp3": "Fear itself, Roosevelt (1933)",
    "audio/armstrong_small_step.mp3": "One small step, Armstrong (1969)",
    "audio/nasa_podcast_artemis.mp3": "NASA podcast: Artemis",
    "audio/jana_gana_mana_1942.mp3": "Jana Gana Mana (1942)",
    "audio/vande_mataram_vaze.mp3": "Vande Mataram, Chandrashekhar Vaze",
    "audio/sitar_raga_yaman.mp3": "Raga Yaman on sitar",
    "audio/moonlight_sonata_allegretto.mp3": "Moonlight Sonata, Allegretto",
    "audio/carefree_macleod.mp3": "Carefree, Kevin MacLeod",
    "audio/windswept_macleod.mp3": "Windswept, Kevin MacLeod",
    "video/hyderabad_traffic.mp4": "Traffic in Hyderabad",
    "video/jalebi_bangalore.mp4": "Jalebi being made, Bangalore",
    "video/obbattu_bakery.mp4": "Obbattu at a bakery, Bengaluru",
    "video/stray_cattle_delhi.mp4": "Cattle on a Delhi road",
    "video/heavy_rain_street.mp4": "Heavy rain on a street",
    "video/cricket_cover_drives.mp4": "Batsman hitting cover drives",
    "video/shivajinagar_bus_station.mp4": "Shivajinagar bus station, Bangalore",
    "video/nasa_west_antarctic.mp4": "West Antarctic ice, NASA",
    "docs/constitution_preamble.pdf": "Constitution of India, Preamble",
    "docs/gandhi_letter_to_roosevelt.pdf": "Gandhi's letter to Roosevelt (1942)",
    "docs/antoines_menu_1920s.pdf": "Antoine's restaurant menu, 1920s",
    "docs/india_monsoon_floods_2018.pdf": "India monsoon floods report, 2018",
    "docs/mars_pathfinder_press_kit.pdf": "Mars Pathfinder press kit, NASA (1997)",
    "docs/hindustan_times_15_aug_1947.jpg": "Hindustan Times, 15 August 1947",
    "docs/food_receipt.jpg": "Food receipt",
    "docs/pound_cake_recipe_card.jpg": "Handwritten pound cake recipe"
}


def get(url: str) -> bytes:
    for attempt in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300).read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(6 * (attempt + 1))


def info(title: str, video: bool = False) -> dict:
    q = {"action": "query", "titles": "File:" + title, "format": "json",
         "prop": "imageinfo|videoinfo" if video else "imageinfo",
         "iiprop": "url|extmetadata", "iiurlwidth": 800,
         "iiextmetadatafilter": "LicenseShortName|Artist"}
    if video:
        q.update({"viprop": "derivatives"})
    page = next(iter(json.loads(get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(q)))["query"]["pages"].values()))
    time.sleep(1.5)
    return page


def credit(page: dict) -> dict:
    meta = page["imageinfo"][0].get("extmetadata", {})
    artist = re.sub("<[^>]+>", "", meta.get("Artist", {}).get("value", "unknown")).strip()
    return {"source": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(page["title"].replace(" ", "_")),
            "author": artist, "license": meta.get("LicenseShortName", {}).get("value", "see source")}


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def trim_args(start, dur):
    return (["-ss", start] if start else []) + (["-t", dur] if dur else [])


def main():
    for d in ("images", "audio", "video", "docs"):
        (LIB / d).mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    credits_path = LIB / "CREDITS.json"
    credits = json.loads(credits_path.read_text(encoding="utf-8")) if credits_path.exists() else {}

    for key, title in IMAGES.items():
        out = LIB / "images" / f"{key}.jpg"
        if not out.exists():
            page = info(title)
            out.write_bytes(get(page["imageinfo"][0]["thumburl"].split("?")[0]))
            credits[f"images/{out.name}"] = credit(page)
        print("image", key)

    for key, (title, start, dur) in AUDIO.items():
        out = LIB / "audio" / f"{key}.mp3"
        if not out.exists():
            page = info(title)
            src = CACHE / Path(urllib.parse.unquote(page["imageinfo"][0]["url"].split("?")[0])).name
            if not src.exists():
                src.write_bytes(get(page["imageinfo"][0]["url"].split("?")[0]))
            ffmpeg(*trim_args(start, dur), "-i", src, "-vn", "-ac", "1", "-b:a", "96k", out)
            credits[f"audio/{out.name}"] = credit(page)
        print("audio", key)

    for key, (title, start, dur) in VIDEO.items():
        out = LIB / "video" / f"{key}.mp4"
        if not out.exists():
            page = info(title, video=True)
            # a small transcode (480p or less) instead of the 4K original
            derivs = page.get("videoinfo", [{}])[0].get("derivatives", [])
            small = [d for d in derivs if d.get("height") and d["height"] <= 480]
            url = (max(small, key=lambda d: d["height"])["src"] if small else page["imageinfo"][0]["url"]).split("?")[0]
            src = CACHE / f"{key}{Path(urllib.parse.urlparse(url).path).suffix}"
            if not src.exists():
                src.write_bytes(get(url))
            ffmpeg(*trim_args(start, dur), "-i", src, "-vf", "scale=-2:'min(480,ih)'", "-c:v", "libx264",
                   "-preset", "veryfast", "-crf", "26", "-c:a", "aac", "-b:a", "96k", "-ac", "1", "-movflags", "+faststart", out)
            credits[f"video/{out.name}"] = credit(page)
        print("video", key)

    for key, (title, pages) in DOCS.items():
        out = LIB / "docs" / f"{key}.pdf"
        if not out.exists():
            page = info(title)
            src = CACHE / f"{key}.pdf"
            if not src.exists():
                src.write_bytes(get(page["imageinfo"][0]["url"].split("?")[0]))
            # keep only the first pages, so the library stays small
            info_out = subprocess.run(["pdfinfo", str(src)], capture_output=True, text=True).stdout
            total = int(re.search(r"Pages:\s+(\d+)", info_out)[1])
            keep = [p for p in (pages if isinstance(pages, list) else range(1, pages + 1)) if p <= total]
            subprocess.run(["pdfseparate", "-l", str(max(keep)), str(src), str(CACHE / f"{key}-p%d.pdf")], check=True)
            subprocess.run(["pdfunite", *[str(CACHE / f"{key}-p{i}.pdf") for i in keep], str(out)], check=True)
            credits[f"docs/{out.name}"] = credit(page)
        print("doc", key)

    for key, title in SCANS.items():
        out = LIB / "docs" / f"{key}.jpg"
        if not out.exists():
            page = info(title)
            url = page["imageinfo"][0].get("thumburl") or page["imageinfo"][0]["url"]
            out.write_bytes(get(url.split("?")[0].replace("/800px-", "/1200px-")))
            credits[f"docs/{out.name}"] = credit(page)
        print("scan", key)

    for k, t in TITLES.items():
        if k in credits:
            credits[k]["title"] = t
    credits_path.write_text(json.dumps(credits, indent=1, ensure_ascii=False), encoding="utf-8")
    print("done:", {d: len(list((LIB / d).iterdir())) for d in ("images", "audio", "video", "docs")})


if __name__ == "__main__":
    main()
