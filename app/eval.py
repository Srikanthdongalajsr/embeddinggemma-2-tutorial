"""Check the search on the real library: does each query put the right file first?

Uses the same text-only model and the same file-level ranking as the search page.
Run after indexing: python app/eval.py
"""
import os
import sys

os.environ["OPEN"] = "0"
sys.path.insert(0, os.path.dirname(__file__))
sys.stdout.reconfigure(encoding="utf-8")

from server import search  # noqa: E402  (loads the text-only model + index)

# query: the file that should come first (and for speech, roughly where)
CASES = {
    "red car": "images/park_town_signal_chennai.jpg",
    "a sign that says wear helmet": "images/park_town_signal_chennai.jpg",
    "yellow taxi": "images/kolkata_street_food_taxi.jpg",
    "colourful powder heaps in a shop": "images/colour_powders_kochi.jpg",
    "kids in a classroom raising their hands": "images/classroom.jpg",
    "students learning to code on computers": "images/coding_class_bangalore.jpg",
    "crowded railway platform": "images/mumbai_station_rush.jpg",
    "a woman cutting vegetables": "images/kitchen_cooking.jpg",
    "family dinner with roast turkey": "images/dinner_table_1971.jpg",
    "boys playing cricket near snowy mountains": "images/street_cricket_mountains.jpg",
    "people under umbrellas on a busy beach": "images/crowded_beach.jpg",
    "an old white car next to a fruit cart": "images/lime_soda_cart.jpg",
    "we choose to go to the moon": "audio/jfk_rice_moon_speech.mp3",
    "at the stroke of the midnight hour India will awake to life and freedom": "audio/nehru_tryst_with_destiny.mp3",
    "the only thing we have to fear is fear itself": "audio/fdr_fear_itself.mp3",
    "one small step for man": "audio/armstrong_small_step.mp3",
    "there is an indefinable mysterious power that pervades everything": "audio/gandhi_spiritual_message.mp3",
    "a podcast about the Artemis moon mission": "audio/nasa_podcast_artemis.mp3",
    "India's national anthem": "audio/jana_gana_mana_1942.mp3",
    "Indian classical sitar music": "audio/sitar_raga_yaman.mp3",
    "a man singing a devotional song": "audio/vande_mataram_vaze.mp3",
    "slow piano music": "audio/moonlight_sonata_allegretto.mp3",
    "happy upbeat background music": "audio/carefree_macleod.mp3",
    "frying sweets in hot oil": "video/jalebi_bangalore.mp4",
    "cows walking on the road": "video/stray_cattle_delhi.mp4",
    "heavy rain on a street": "video/heavy_rain_street.mp4",
    "a batsman hitting the ball": "video/cricket_cover_drives.mp4",
    "ice melting in Antarctica": "video/nasa_west_antarctic.mp4",
    "a baker making flatbread": "video/obbattu_bakery.mp4",
    "busy traffic with auto rickshaws": "video/hyderabad_traffic.mp4",
    # documents: PDFs (text + page pictures) and scanned photos of text
    "we the people of India": "docs/constitution_preamble.pdf",
    "a letter asking America to support India's freedom": "docs/gandhi_letter_to_roosevelt.pdf",
    "oysters and turtle soup on the menu": "docs/antoines_menu_1920s.pdf",
    "map of flood affected districts in Kerala": "docs/india_monsoon_floods_2018.pdf",
    "a rover named Sojourner": "docs/mars_pathfinder_press_kit.pdf",
    "newspaper headline about India's independence": "docs/hindustan_times_15_aug_1947.jpg",
    "a restaurant bill": "docs/food_receipt.jpg",
    "a handwritten cake recipe": "docs/pound_cake_recipe_card.jpg",
}


def mmss(t):
    return f"{int(t) // 60}:{int(t) % 60:02d}"


if __name__ == "__main__":
    hits = 0
    for q, want in CASES.items():
        res = search(q, k=40, dim=768, each=False)["results"]
        files = [r["file"] for r in res]
        rank = files.index(want) + 1 if want in files else 99
        hits += rank == 1
        top = res[0]
        where = (f" p{top['page']} {top['part']}" if top["kind"] == "doc"
                 else f" @{mmss(top['start'])} {top['part']}" if top["kind"] != "image" else "")
        print(f"{'OK ' if rank == 1 else f'r{rank:<2}'} {q[:55]:55} -> {top['file']}{where} {top['score']:.2f}")
    print(f"\n{hits}/{len(CASES)} first")
