"""Download the "plant" library: real factory photos, machine sounds, shop-floor videos and maintenance/safety
documents, for the manufacturing version of the demo. Everything is public domain or Creative Commons (BY / BY-SA);
credits go to plant/library/CREDITS.json.

Six topics, each in several file types, so grouping has something real to find:
1 pumps, motors, bearings  2 welding  3 conveyors and forklifts  4 corrosion and leaks  5 compressors  6 electrical safety

Sources: Wikimedia Commons (via get_library's helpers), the MIMII machine-sound dataset on Zenodo (single WAVs read
out of the 7.7 GB zip with HTTP range requests), and US federal works (CDC/NIOSH, OSHA), which are public domain.

Run: python app/get_plant.py   (needs ffmpeg and poppler on PATH), then:  set WORKSPACE=plant && python app/indexer.py
"""
import json
import re
import struct
import subprocess
import time
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

from get_library import UA, credit, ffmpeg, get, info, trim_args

ROOT = Path(__file__).resolve().parent.parent / "plant"
LIB = ROOT / "library"
CACHE = ROOT / ".cache" / "downloads"

# key: (Commons title, topic)
IMAGES = {
    "centrifugal_pump_belt_drive": ("Warman centrifugal pump.jpg", 1),
    "inline_pumps_motors": ("Centrifugal Pump.jpg", 1),
    "bearing_shell_overheat": ("Cologne Germany Overheating-marks-at-a-bearing-shell-01.jpg", 1),
    "weld_crack_stress_corrosion": ("Stress-Corrosion-Cracking-caused-by-weld-stress-01.jpg", 2),
    "welder_arc_helmet": ("A job weld done (8043734).jpg", 2),
    "pipe_stick_welding": ("SMAW.jpg", 2),
    "roller_conveyor_line": ("Conveyor system in a factory.jpg", 3),
    "forklifts_warehouse": ("Forklift.jpeg", 3),
    "forklift_moving_pallet": ("Workers drive Forklifts laden with USAID goods inside a large warehouse - 20110826-FS-LSC-0138 - Flickr - USDAgov.jpg", 3),
    "rusty_gate_valve": ("Rusty Valve.jpg", 4),
    "plant_room_rusty_valves": ("Rusty pipes.jpg", 4),
    "pipe_surface_rust": ("Rusty pipes (7463495770).jpg", 4),
    "screw_compressor_motor": ("Screw compressor 1.jpg", 5),
    "piston_air_compressor": ("Air compressor in engine room.JPG", 5),
    "valve_pressure_gauge": ("Close-up view of a red valve on a metallic pipe system with a pressure gauge in an industrial setting.jpg", 5),
    "lockout_padlocks_isolators": ("Power Lockout (13421721974).jpg", 6),
    "breaker_locked_tagged": ("Glavno stikalo, zavarovano pred neželenim vklopom.JPG", 6),
    "arc_flash_ppe": ("Pueblo Chemical Agent-Destruction Pilot Plant Protection Gear (5571650875).jpg", 6),
}

# key: (Commons title, start s, duration s or None, topic)
AUDIO = {
    "pump_submersible_running": ("WWS Submersiblepump.ogg", 0, None, 1),
    "air_compressor_running": ("WWS Aircompressor.ogg", 0, None, 5),
    "steam_release_hiss": ("WWS SteamlocomotiveS06-018Steamrelease.ogg", 0, None, 4),
    "air_leak_hiss": ("Air duster.ogg", 0, None, 4),
    "welding_mig": ("WWS Welding.ogg", 0, None, 2),
    "conveyor_belt": ("WWS Conveyorbelt.ogg", 0, None, 3),
    "forklift_truck": ("WWS Forklifttruck.ogg", 0, None, 3),
    "bench_grinder": ("WWS DoubleEndedGrinder.ogg", 0, None, 1),
}
# Spoken safety briefing cut from the NIOSH "Arc Flash Awareness" film (US federal work), read from the 240p transcode
NIOSH_FILM = "Arc Flash Awareness.webm"
NIOSH_URL = "https://upload.wikimedia.org/wikipedia/commons/transcoded/1/11/Arc_Flash_Awareness.webm/Arc_Flash_Awareness.webm.240p.vp9.webm"
NIOSH_CLIPS = {"niosh_arc_flash_briefing": (73, 113), "niosh_lockout_briefing": (1457, 64)}
# MIMII (Purohit et al., Hitachi, CC BY-SA 4.0): the same factory pump, healthy and faulty, 10 s each, channel 0
MIMII_URL = "https://zenodo.org/records/3384388/files/6_dB_pump.zip?download=1"
MIMII = {"pump_normal_mimii": "pump/id_00/normal/00000000.wav", "pump_faulty_mimii": "pump/id_00/abnormal/00000000.wav"}

# key: (Commons title, start s, duration s or None, topic)
VIDEO = {
    "hydraulic_motor_pump_unit": ("Hydraulic aggregate for the calender.webm", 0, None, 1),
    "automated_weld_pressure_vessel": ("Orion Pressure Vessel V Final Weld (20250801 Orion ArtV-FinalWeld VoY).webm", 0, 60, 2),
    "butt_welding_machine": ("Automatic butt-welding machine.webm", 0, None, 2),
    "belt_conveyor_coal": ("The Velenje Coal Mine, Coal transport from longwall face with belt conveyor.webm", 0, None, 3),
    "forklift_training": ("JFC-UA Service Members Train NGOs, Liberians on Forklift 150110-A-YW926-001.webm", 0, None, 3),
    "cnc_lathe_turning": ("Denford Novaturn CNC Lathe (video) - Nottingham Hackspace.webm", 0, None, 1),
    "air_compressor_blowing": ("Cleaning a chainsaw with old air compressor.webm", 0, None, 5),
    "compressor_gas_leak_camera": ("Ultrasound Leak CH-methane-VOC leak detection, reciprocating compressor.webm", 0, None, 4),
    "electrical_arc_flash": ("Electrical arc flash.webm", 0, None, 6),
}

# PDFs from US federal sites (public domain, 17 USC 105). Only pages without third-party material are kept.
# key: (url, PDF pages to keep (1-based), publisher, topic)
OSHA = "https://www.osha.gov/sites/default/files/publications/"
TM5_692_1 = "https://www.wbdg.org/FFC/ARMYCOE/COETM/tm_5_692_1.pdf"
DOCS = {
    "pump_troubleshooting_ufc": ("https://www.wbdg.org/FFC/DOD/UFC/ARCHIVES/ufc_3_230_02_2001.pdf", [100, 101, 104, 105],
                                 "US Department of Defense, UFC 3-230-02 (2001)", 1),
    "centrifugal_pump_manual_1946": ("https://upload.wikimedia.org/wikipedia/commons/7/78/TM_5-2044_Pump%2C_Centrifugal%2C_Gasoline_Engine_Driven%2C_Base_Mounted%2C_2_Inch_Discharge%2C_166_GPM_At_25_Foot_Head%2C_Novo%2C_Model_KH_2%2C_With_Novo_Model_CA_33_Engine_1946_%28IA_TM5-2044%29.pdf",
                                     [26, 34, 35, 36], "US War Department, TM 5-2044 (1946)", 1),
    "weld_defects_army_tc9_237": ("https://armypubs.army.mil/epubs/DR_pubs/DR_a/pdf/web/tc9_237.pdf", [641, 642, 643, 644],
                                  "US Department of the Army, TC 9-237 (1993)", 2),
    "welding_fumes_osha": (OSHA + "OSHA_FS-3647_Welding.pdf", [2], "OSHA, FS-3647 (2013)", 2),
    "conveyor_guarding_osha": (OSHA + "OSHA3170.pdf", [29, 30, 31], "OSHA 3170 (2007)", 3),
    "forklift_safety_osha": (OSHA + "OSHA3949.pdf", [1], "OSHA QuickCard 3949 (2019)", 3),
    "pipe_corrosion_rupture_csb": ("https://www.csb.gov/assets/1/20/chevron_final_investigation_report_2015-01-28.pdf",
                                   [21, 32, 45, 50], "US Chemical Safety Board, report 2012-03-I-CA (2015)", 4),
    "corrosion_protection_army": (TM5_692_1, [220, 221, 223, 224], "US Department of the Army, TM 5-692-1 (2005)", 4),
    "compressed_air_maintenance_army": (TM5_692_1, [128, 130, 131, 132, 133], "US Department of the Army, TM 5-692-1 (2005)", 5),
    "lockout_tagout_osha": (OSHA + "OSHA3120.pdf", [7, 13, 14, 15], "OSHA 3120 (2002)", 6),
    "arc_flash_osha": (OSHA + "OSHA4472.pdf", [5, 8, 10, 12], "OSHA 4472 (2024)", 6),
}
BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/pdf,*/*"}   # osha.gov refuses other agents

TITLES = {
    "images/centrifugal_pump_belt_drive.jpg": "Centrifugal pump on a belt drive",
    "images/inline_pumps_motors.jpg": "Two inline pumps in a plant room",
    "images/bearing_shell_overheat.jpg": "Bearing shell with overheating marks",
    "images/weld_crack_stress_corrosion.jpg": "Cracks next to a weld",
    "images/welder_arc_helmet.jpg": "Welder at work",
    "images/pipe_stick_welding.jpg": "Stick welding a pipe",
    "images/roller_conveyor_line.jpg": "Conveyor lines in a factory",
    "images/forklifts_warehouse.jpg": "Forklifts by the racks",
    "images/forklift_moving_pallet.jpg": "Forklift moving a pallet stack",
    "images/rusty_gate_valve.jpg": "Rusted gate valve",
    "images/plant_room_rusty_valves.jpg": "Rusted valves and flanges",
    "images/pipe_surface_rust.jpg": "Flaking rust on pipes",
    "images/screw_compressor_motor.jpg": "Screw compressor and motor",
    "images/piston_air_compressor.jpg": "Piston air compressor",
    "images/valve_pressure_gauge.jpg": "Valve and pressure gauge",
    "images/lockout_padlocks_isolators.jpg": "Lockout padlocks on isolators",
    "images/breaker_locked_tagged.jpg": "Breaker locked and tagged",
    "images/arc_flash_ppe.jpg": "Putting on arc flash gear",
    "audio/pump_submersible_running.mp3": "Submersible pump running",
    "audio/air_compressor_running.mp3": "Air compressor running",
    "audio/steam_release_hiss.mp3": "Steam release",
    "audio/air_leak_hiss.mp3": "Compressed air hiss",
    "audio/welding_mig.mp3": "MIG welding",
    "audio/conveyor_belt.mp3": "Belt conveyor running",
    "audio/forklift_truck.mp3": "Forklift at work",
    "audio/bench_grinder.mp3": "Bench grinder",
    "audio/niosh_arc_flash_briefing.mp3": "Arc flash briefing, NIOSH",
    "audio/niosh_lockout_briefing.mp3": "De-energize and lock out, NIOSH",
    "audio/pump_normal_mimii.mp3": "Factory pump, healthy",
    "audio/pump_faulty_mimii.mp3": "Factory pump, faulty",
    "video/hydraulic_motor_pump_unit.mp4": "Hydraulic pump unit running",
    "video/automated_weld_pressure_vessel.mp4": "Automated weld on a pressure vessel, NASA",
    "video/butt_welding_machine.mp4": "Butt welding machine",
    "video/belt_conveyor_coal.mp4": "Belt conveyor in a mine",
    "video/forklift_training.mp4": "Forklift training",
    "video/cnc_lathe_turning.mp4": "CNC lathe turning a part",
    "video/air_compressor_blowing.mp4": "Air compressor in use",
    "video/compressor_gas_leak_camera.mp4": "Leak found on a compressor",
    "video/electrical_arc_flash.mp4": "Electrical arc flash",
    "docs/pump_troubleshooting_ufc.pdf": "Centrifugal pump troubleshooting, DoD",
    "docs/centrifugal_pump_manual_1946.pdf": "Centrifugal pump manual, US Army (1946)",
    "docs/weld_defects_army_tc9_237.pdf": "Weld defects and causes, US Army",
    "docs/welding_fumes_osha.pdf": "Welding fumes, OSHA",
    "docs/conveyor_guarding_osha.pdf": "Conveyor hazards and guards, OSHA",
    "docs/forklift_safety_osha.pdf": "Forklift safety, OSHA",
    "docs/pipe_corrosion_rupture_csb.pdf": "Corroded pipe rupture, Chevron refinery (CSB)",
    "docs/corrosion_protection_army.pdf": "Cathodic protection troubleshooting, US Army",
    "docs/compressed_air_maintenance_army.pdf": "Compressed air maintenance, US Army",
    "docs/lockout_tagout_osha.pdf": "Lockout/tagout steps, OSHA",
    "docs/arc_flash_osha.pdf": "Arc flash hazards, OSHA",
}


def fetch(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.write_bytes(get(url))
        time.sleep(4)            # upload.wikimedia.org answers 429 to quick bursts
    return dest


def ranged(url: str, a: int, b: int) -> bytes:
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=dict(UA, Range=f"bytes={a}-{b}"))
            return urllib.request.urlopen(req, timeout=120).read()
        except Exception:
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))


def zip_member(url: str, want: set) -> dict:
    """Read single files out of a big remote zip (zip64 aware) using HTTP range requests."""
    size = int(urllib.request.urlopen(urllib.request.Request(url, headers=dict(UA, Range="bytes=0-0")),
                                      timeout=60).headers["Content-Range"].split("/")[1])
    tail = ranged(url, size - 65557, size - 1)
    cd_size, cd_off = struct.unpack("<II", tail[tail.rfind(b"PK\x05\x06") + 12:][:8])
    loc = tail.rfind(b"PK\x06\x07")                  # zip64 end-of-central-directory locator
    if loc >= 0:
        z64 = ranged(url, *(lambda o: (o, o + 55))(struct.unpack("<Q", tail[loc + 8:loc + 16])[0]))
        cd_size, cd_off = struct.unpack("<QQ", z64[40:56])
    cd, p, found = ranged(url, cd_off, cd_off + cd_size - 1), 0, {}
    while cd[p:p + 4] == b"PK\x01\x02":
        method, = struct.unpack("<H", cd[p + 10:p + 12])
        csz, usz = struct.unpack("<II", cd[p + 20:p + 28])
        fl, el, cl = struct.unpack("<HHH", cd[p + 28:p + 34])
        off, = struct.unpack("<I", cd[p + 42:p + 46])
        name = cd[p + 46:p + 46 + fl].decode()
        extra, q = cd[p + 46 + fl:p + 46 + fl + el], 0
        while q + 4 <= len(extra):                   # zip64 extra field holds the real sizes/offset
            tag, ln = struct.unpack("<HH", extra[q:q + 4])
            if tag == 1:
                vals, r = extra[q + 4:q + 4 + ln], 0
                if usz == 0xFFFFFFFF: usz, = struct.unpack("<Q", vals[r:r + 8]); r += 8
                if csz == 0xFFFFFFFF: csz, = struct.unpack("<Q", vals[r:r + 8]); r += 8
                if off == 0xFFFFFFFF: off, = struct.unpack("<Q", vals[r:r + 8])
            q += 4 + ln
        if name in want:
            head = ranged(url, off, off + 29)
            n, m = struct.unpack("<HH", head[26:30])
            data = ranged(url, off + 30 + n + m, off + 30 + n + m + csz - 1)
            found[name] = data if method == 0 else zlib.decompress(data, -15)
        p += 46 + fl + el + cl
    return found


def save(credits: dict):
    (LIB / "CREDITS.json").write_text(json.dumps(credits, indent=1, ensure_ascii=False), encoding="utf-8")


def main():
    for d in ("images", "audio", "video", "docs"):
        (LIB / d).mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    credits_path = LIB / "CREDITS.json"
    credits = json.loads(credits_path.read_text(encoding="utf-8")) if credits_path.exists() else {}

    for key, (title, _) in IMAGES.items():
        out = LIB / "images" / f"{key}.jpg"
        if f"images/{out.name}" not in credits:
            page = info(title)
            fetch(page["imageinfo"][0]["thumburl"].split("?")[0], out)
            credits[f"images/{out.name}"] = credit(page)
            save(credits)
        print("image", key, flush=True)

    for key, (title, start, dur, _) in AUDIO.items():
        out = LIB / "audio" / f"{key}.mp3"
        if f"audio/{out.name}" not in credits:
            page = info(title)
            if not out.exists():
                url = page["imageinfo"][0]["url"].split("?")[0]
                src = fetch(url, CACHE / Path(urllib.parse.unquote(url)).name)
                ffmpeg(*trim_args(start, dur), "-i", src, "-vn", "-ac", "1", "-b:a", "96k", out)
            credits[f"audio/{out.name}"] = credit(page)
            save(credits)
        print("audio", key, flush=True)

    film = None
    for key, (start, dur) in NIOSH_CLIPS.items():
        out = LIB / "audio" / f"{key}.mp3"
        if f"audio/{out.name}" not in credits:
            film = film or info(NIOSH_FILM, video=True)
            out.exists() or ffmpeg("-ss", start, "-t", dur, "-user_agent", UA["User-Agent"], "-i", NIOSH_URL,
                   "-vn", "-ac", "1", "-b:a", "96k", out)
            credits[f"audio/{out.name}"] = dict(credit(film), note=f"audio clip {start}-{start + dur} s")
        print("audio", key, flush=True)

    todo = {k: m for k, m in MIMII.items() if not (LIB / "audio" / f"{k}.mp3").exists()}
    if todo:
        got = zip_member(MIMII_URL, set(todo.values()))
        for key, member in todo.items():
            wav = CACHE / f"{key}.wav"
            wav.write_bytes(got[member])
            ffmpeg("-i", wav, "-af", "pan=mono|c0=c0", "-b:a", "96k", LIB / "audio" / f"{key}.mp3")
            credits[f"audio/{key}.mp3"] = {
                "source": "https://zenodo.org/records/3384388", "license": "CC BY-SA 4.0",
                "author": "Purohit, Tanabe, Ichige, Endo, Nikaido, Suefusa, Kawaguchi (Hitachi), MIMII dataset",
                "note": f"6_dB_pump.zip: {member}, channel 0"}
        save(credits)
    print("audio mimii", flush=True)

    for key, (title, start, dur, _) in VIDEO.items():
        out = LIB / "video" / f"{key}.mp4"
        if not out.exists():
            page = info(title, video=True)
            derivs = page.get("videoinfo", [{}])[0].get("derivatives", [])
            small = [d for d in derivs if d.get("height") and d["height"] <= 480]
            url = (max(small, key=lambda d: d["height"])["src"] if small else page["imageinfo"][0]["url"]).split("?")[0]
            src = fetch(url, CACHE / f"{key}{Path(urllib.parse.urlparse(url).path).suffix}")
            ffmpeg(*trim_args(start, dur), "-i", src, "-vf", "scale=-2:'min(480,ih)'", "-c:v", "libx264",
                   "-preset", "veryfast", "-crf", "26", "-c:a", "aac", "-b:a", "96k", "-ac", "1", "-movflags", "+faststart", out)
            credits[f"video/{out.name}"] = credit(page)
            save(credits)
        print("video", key, flush=True)

    for key, (url, pages, publisher, _) in DOCS.items():
        out = LIB / "docs" / f"{key}.pdf"
        if not out.exists():
            src = CACHE / (Path(urllib.parse.urlparse(url).path).name or f"{key}.pdf")
            if not src.exists():
                src.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=BROWSER if "osha.gov" in url else UA),
                                                       timeout=300).read())
            total = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(src)], capture_output=True, text=True).stdout)[1])
            keep = [p for p in pages if p <= total]
            subprocess.run(["pdfseparate", "-f", str(min(keep)), "-l", str(max(keep)), str(src), str(CACHE / f"{key}-p%d.pdf")], check=True)
            subprocess.run(["pdfunite", *[str(CACHE / f"{key}-p{i}.pdf") for i in keep], str(out)], check=True)
            credits[f"docs/{out.name}"] = {"source": url, "author": publisher,
                                           "license": "Public domain (US federal work)", "note": f"PDF pages {keep}"}
            save(credits)
        print("doc", key, flush=True)

    for k, t in TITLES.items():
        if k in credits:
            credits[k]["title"] = t
    save(credits)
    print("done:", {d: len(list((LIB / d).iterdir())) for d in ("images", "audio", "video", "docs")})


if __name__ == "__main__":
    main()
