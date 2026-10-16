import os
import sys

os.environ["OPEN"] = "0"
os.environ.setdefault("WORKSPACE", "plant")
sys.path.insert(0, os.path.dirname(__file__))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402

from server import search, state  # noqa: E402

RUST = {"images/rusty_gate_valve.jpg", "images/plant_room_rusty_valves.jpg", "images/pipe_surface_rust.jpg"}
LOCKOUT = {"images/breaker_locked_tagged.jpg", "images/lockout_padlocks_isolators.jpg"}
WELD_VIDEO = {"video/butt_welding_machine.mp4", "video/automated_weld_pressure_vessel.mp4"}
PUMP = {"docs/pump_troubleshooting_ufc.pdf", "docs/centrifugal_pump_manual_1946.pdf", "audio/pump_submersible_running.mp3",
        "audio/pump_normal_mimii.mp3", "audio/pump_faulty_mimii.mp3", "images/centrifugal_pump_belt_drive.jpg",
        "images/inline_pumps_motors.jpg", "video/hydraulic_motor_pump_unit.mp4"}

# query: files that count as right (written before indexing; two frozen queries had no matching file, see below)
CASES = {
    # photos
    "rusted pipe flange": RUST,
    "a cracked weld": {"images/weld_crack_stress_corrosion.jpg"},
    "padlock and tag on an electrical switch": LOCKOUT,
    "damaged bearing": {"images/bearing_shell_overheat.jpg"},
    # videos
    "forklift moving pallets in a warehouse": {"video/forklift_training.mp4", "images/forklift_moving_pallet.jpg"},
    "sparks flying from welding": WELD_VIDEO | {"images/welder_arc_helmet.jpg", "images/pipe_stick_welding.jpg"},
    "boxes moving on a conveyor": {"images/roller_conveyor_line.jpg", "video/belt_conveyor_coal.mp4"},
    # sounds
    "hissing sound of an air leak": {"audio/air_leak_hiss.mp3", "audio/steam_release_hiss.mp3"},
    "loud air compressor running": {"audio/air_compressor_running.mp3", "video/air_compressor_blowing.mp4"},
    "beeping of a reversing forklift": {"audio/forklift_truck.mp3"},   # no beeper in the library: nearest is the forklift
    # manual pages
    "pump is noisy and vibrating, what could be the cause": {"docs/pump_troubleshooting_ufc.pdf"},
    "steps to lock out a machine before maintenance": {"docs/lockout_tagout_osha.pdf"},
    "how to stay safe from welding fumes": {"docs/welding_fumes_osha.pdf"},
    # Telugu (typed query, English files)
    "పంప్ నుంచి చాలా శబ్దం వస్తోంది": PUMP,
    "వెల్డింగ్ పొగ": {"docs/welding_fumes_osha.pdf"},
    "కన్వేయర్ జామ్ అయింది": {"docs/conveyor_guarding_osha.pdf", "images/roller_conveyor_line.jpg", "video/belt_conveyor_coal.mp4", "audio/conveyor_belt.mp3"},
}
# The real pain: a technician on a breakdown types the SYMPTOM, the way they'd say it, and needs everything the plant
# already knows about it, spread across manuals, photos, recordings and videos. Each symptom lists what should come
# back per kind. (Added 2026-10-14 while the index was still building, before any result was seen.)
SYMPTOMS = {
    "pump is vibrating badly and the bearing housing is getting hot": {
        "doc": {"docs/pump_troubleshooting_ufc.pdf", "docs/centrifugal_pump_manual_1946.pdf"},
        "image": {"images/bearing_shell_overheat.jpg", "images/centrifugal_pump_belt_drive.jpg", "images/inline_pumps_motors.jpg"},
        "audio": {"audio/pump_submersible_running.mp3", "audio/pump_faulty_mimii.mp3", "audio/pump_normal_mimii.mp3"},
        "video": {"video/hydraulic_motor_pump_unit.mp4"}},
    "air pressure keeps dropping on the line and we can hear hissing": {
        "doc": {"docs/compressed_air_maintenance_army.pdf"},
        "image": {"images/valve_pressure_gauge.jpg", "images/piston_air_compressor.jpg", "images/screw_compressor_motor.jpg"},
        "audio": {"audio/air_leak_hiss.mp3", "audio/steam_release_hiss.mp3"},
        "video": {"video/compressor_gas_leak_camera.mp4", "video/air_compressor_blowing.mp4"}},
    "new welds on the frame are cracking": {
        "doc": {"docs/weld_defects_army_tc9_237.pdf"},
        "image": {"images/weld_crack_stress_corrosion.jpg"},
        "audio": {"audio/welding_mig.mp3"},
        "video": WELD_VIDEO},
    "operator's hand got caught clearing a jam on the conveyor": {
        "doc": {"docs/conveyor_guarding_osha.pdf", "docs/lockout_tagout_osha.pdf"},
        "image": {"images/roller_conveyor_line.jpg", "images/lockout_padlocks_isolators.jpg"},
        "audio": {"audio/conveyor_belt.mp3"},
        "video": {"video/belt_conveyor_coal.mp4"}},
    "old pipe is thinning and started dripping under the insulation": {
        "doc": {"docs/pipe_corrosion_rupture_csb.pdf", "docs/corrosion_protection_army.pdf"},
        "image": RUST,
        "audio": {"audio/steam_release_hiss.mp3", "audio/air_leak_hiss.mp3"},
        "video": {"video/compressor_gas_leak_camera.mp4"}},
    "electrician needs to work on the panel, is switching it off enough": {
        "doc": {"docs/arc_flash_osha.pdf", "docs/lockout_tagout_osha.pdf"},
        "image": LOCKOUT | {"images/arc_flash_ppe.jpg"},
        "audio": {"audio/niosh_lockout_briefing.mp3", "audio/niosh_arc_flash_briefing.mp3"},
        "video": {"video/electrical_arc_flash.mp4"}},
}

# Staged technician voice notes recorded by the user (plant/VOICE-NOTES-to-record.md); tested once they exist
VOICE = {
    "grinding noise from pump 3, bearing hot": "audio/voice_note_pump3_bearing",
    "air leak on line 2": "audio/voice_note_line2_air_leak",
    "weld cracks on the frame": "audio/voice_note_frame_weld_cracks",
    "conveyor jam safety": "audio/voice_note_conveyor2_jam",
}

NO_FILE = ["oil leaking from a machine", "frayed conveyor belt"]   # frozen queries with no matching file on Commons


def mmss(t):
    return f"{int(t) // 60}:{int(t) % 60:02d}"


def where(r):
    return (f" p{r['page']}" if r["kind"] == "doc" else f" @{mmss(r['start'])} {r['part']}" if r["kind"] != "image" else "")


if __name__ == "__main__":
    hits = 0
    for q, want in CASES.items():
        res = search(q, k=60)["results"]
        files = [r["file"] for r in res]
        rank = min((files.index(w) + 1 for w in want if w in files), default=99)
        hits += rank == 1
        top = res[0]
        print(f"{'OK ' if rank == 1 else f'r{rank:<2}'} {q[:52]:52} -> {top['file']}{where(top)} {top['score']:.2f}"
              f"   (2nd {res[1]['file']} {res[1]['score']:.2f})")
    print(f"\n{hits}/{len(CASES)} first   (not testable, no file: {', '.join(NO_FILE)})")

    print("\nSYMPTOMS: the best file of each kind, right or not (the 'one search, everything we know' view):")
    right = total = 0
    for q, want in SYMPTOMS.items():
        print(" ", q)
        for r in search(q, each=True)["results"]:
            ok = r["file"] in want.get(r["kind"], set())
            right, total = right + ok, total + 1
            print(f"    {'OK ' if ok else '-- '}{r['kind']:5} {r['file']}{where(r)} {r['score']:.2f}")
    print(f"  {right}/{total} kind-slots right")

    notes = {q: stem for q, stem in VOICE.items() if any(r["file"].startswith(stem + ".") for r in state["rows"])}
    if notes:
        print("\nVOICE NOTES (typed English query -> spoken note):")
        for q, stem in notes.items():
            files = [r["file"] for r in search(q, k=60)["results"]]
            rank = next(i + 1 for i, f in enumerate(files) if f.startswith(stem + "."))
            print(f"  {'OK ' if rank == 1 else f'r{rank:<2}'} {q:42} top: {files[0]}")

    print("\nbest of each kind:")
    for q in ("pump is noisy and vibrating, what could be the cause", "welding", "lockout tagout"):
        print(" ", q, "->", ", ".join(f"{r['kind']}:{r['file'].split('/')[1]} {r['score']:.2f}" for r in search(q, each=True)["results"]))

    print("\nhealthy vs faulty pump (same pump, same mic):")
    rows, vecs = state["rows"], state["vecs"] / np.linalg.norm(state["vecs"], axis=1, keepdims=True)
    idx = {r["file"]: i for i, r in enumerate(rows)}
    n, f = vecs[idx["audio/pump_normal_mimii.mp3"]], vecs[idx["audio/pump_faulty_mimii.mp3"]]
    print(f"  similarity healthy vs faulty: {n @ f:.3f}")
    for q in ("a pump running normally", "a faulty pump making an abnormal noise", "pump making a strange noise"):
        res = {r["file"]: r["score"] for r in search(q, k=60)["results"]}
        print(f"  {q:40} healthy {res.get('audio/pump_normal_mimii.mp3', 0):.3f}  faulty {res.get('audio/pump_faulty_mimii.mp3', 0):.3f}")

    print("\ntiming:", [search(q)["ms"] for q in list(CASES)[:5]], "ms on", search("x")["device"])
