import os
import sys
from pathlib import Path

os.environ["OPEN"] = "0"
os.environ.setdefault("WORKSPACE", "plant")
sys.path.insert(0, os.path.dirname(__file__))
sys.stdout.reconfigure(encoding="utf-8")

from server import ROOT, search  # noqa: E402

A, I, V, D = "audio/", "images/", "video/", "docs/"
PUMP = {D + "pump_troubleshooting_ufc.pdf", D + "centrifugal_pump_manual_1946.pdf", I + "centrifugal_pump_belt_drive.jpg",
        I + "inline_pumps_motors.jpg", I + "bearing_shell_overheat.jpg", A + "pump_submersible_running.mp3",
        A + "pump_normal_mimii.mp3", A + "pump_faulty_mimii.mp3", V + "hydraulic_motor_pump_unit.mp4", A + "voice_note_pump3_bearing.mp3"}
AIR = {D + "compressed_air_maintenance_army.pdf", A + "air_leak_hiss.mp3", A + "steam_release_hiss.mp3", A + "air_compressor_running.mp3",
       I + "piston_air_compressor.jpg", I + "screw_compressor_motor.jpg", I + "valve_pressure_gauge.jpg",
       V + "air_compressor_blowing.mp4", V + "compressor_gas_leak_camera.mp4", A + "voice_note_line2_air_leak.mp3"}
WELD = {D + "weld_defects_army_tc9_237.pdf", D + "welding_fumes_osha.pdf", I + "weld_crack_stress_corrosion.jpg",
        I + "welder_arc_helmet.jpg", I + "pipe_stick_welding.jpg", A + "welding_mig.mp3", V + "butt_welding_machine.mp4",
        V + "automated_weld_pressure_vessel.mp4", A + "voice_note_frame_weld_cracks.mp3"}
CONV = {D + "conveyor_guarding_osha.pdf", D + "lockout_tagout_osha.pdf", I + "roller_conveyor_line.jpg", A + "conveyor_belt.mp3",
        V + "belt_conveyor_coal.mp4", A + "voice_note_conveyor2_jam.mp3"}
CORR = {D + "pipe_corrosion_rupture_csb.pdf", D + "corrosion_protection_army.pdf", I + "rusty_gate_valve.jpg",
        I + "plant_room_rusty_valves.jpg", I + "pipe_surface_rust.jpg", V + "compressor_gas_leak_camera.mp4",
        A + "air_leak_hiss.mp3", A + "steam_release_hiss.mp3", I + "weld_crack_stress_corrosion.jpg"}
ELEC = {D + "arc_flash_osha.pdf", D + "lockout_tagout_osha.pdf", I + "lockout_padlocks_isolators.jpg", I + "breaker_locked_tagged.jpg",
        I + "arc_flash_ppe.jpg", A + "niosh_lockout_briefing.mp3", A + "niosh_arc_flash_briefing.mp3", V + "electrical_arc_flash.mp4"}
FORK = {D + "forklift_safety_osha.pdf", I + "forklifts_warehouse.jpg", I + "forklift_moving_pallet.jpg", A + "forklift_truck.mp3",
        V + "forklift_training.mp4"}
LATHE = {V + "cnc_lathe_turning.mp4"}

# (question, kind of question, right first answers, relevant group)
QS = [
    # symptoms with several clues, in a worker's words (not the manual's)
    ("pump bearings keep failing every few months even after replacing them", "symptom", {D + "pump_troubleshooting_ufc.pdf#4", A + "voice_note_pump3_bearing.mp3"}, PUMP),
    ("pump runs but doesn't build pressure after we restarted it", "symptom", {D + "pump_troubleshooting_ufc.pdf#2"}, PUMP),
    ("pump lost its prime and won't pick up water", "symptom", {D + "pump_troubleshooting_ufc.pdf#1", D + "pump_troubleshooting_ufc.pdf#2", D + "centrifugal_pump_manual_1946.pdf#1"}, PUMP),
    ("motor on the compressor is running hot and shaking", "symptom", {D + "compressed_air_maintenance_army.pdf#3"}, AIR),
    ("water coming out with the compressed air at the tools", "symptom", {D + "compressed_air_maintenance_army.pdf#5"}, AIR),
    ("MIG welds full of tiny holes even though the shielding gas is on", "symptom", {D + "weld_defects_army_tc9_237.pdf#4", D + "weld_defects_army_tc9_237.pdf#2"}, WELD),
    ("weld bead is sitting on top and not fusing into the base metal", "symptom", {D + "weld_defects_army_tc9_237.pdf#1"}, WELD),
    ("welder felt dizzy and sick after working inside the tank", "symptom", {D + "welding_fumes_osha.pdf#1"}, WELD),
    ("found an orange puddle under an insulated hot oil line during rounds", "symptom", {D + "pipe_corrosion_rupture_csb.pdf#2"}, CORR),
    ("why did one section of carbon steel pipe corrode much faster than the next", "symptom", {D + "pipe_corrosion_rupture_csb.pdf#3", D + "pipe_corrosion_rupture_csb.pdf#4"}, CORR),
    ("buried pipeline still rusting even though we have cathodic protection", "symptom", {D + "corrosion_protection_army.pdf#4"}, CORR),
    ("worker reached into a moving belt to pull out a stuck box", "symptom", {D + "conveyor_guarding_osha.pdf#1", D + "conveyor_guarding_osha.pdf#2", A + "voice_note_conveyor2_jam.mp3"}, CONV),
    ("how do we guard the pinch point where the belt meets the roller", "symptom", {D + "conveyor_guarding_osha.pdf#2", D + "conveyor_guarding_osha.pdf#3"}, CONV),
    ("forklift tipped over while carrying a raised load on a slope", "symptom", {D + "forklift_safety_osha.pdf#1"}, FORK),
    # safety rules, where the exact page matters
    ("who is allowed to remove my padlock after the repair is done", "page", {D + "lockout_tagout_osha.pdf#4"}, ELEC),
    ("I switched off the breaker, can I start working on the panel now", "page", {D + "arc_flash_osha.pdf#1", A + "niosh_lockout_briefing.mp3", D + "lockout_tagout_osha.pdf#3"}, ELEC),
    ("what arc rating does my clothing need for a category 2 job", "page", {D + "arc_flash_osha.pdf#4"}, ELEC),
    ("how close can an unqualified person get to live equipment", "page", {D + "arc_flash_osha.pdf#2"}, ELEC),
    ("what should I check before trusting that the energy is really isolated", "page", {D + "lockout_tagout_osha.pdf#3", A + "niosh_lockout_briefing.mp3"}, ELEC),
    # the plant's own experience (the staged voice notes)
    ("has pump 3 had this grinding problem before and what did we do", "own note", {A + "voice_note_pump3_bearing.mp3"}, PUMP),
    ("someone said there's a leak behind the compressor, where was it", "own note", {A + "voice_note_line2_air_leak.mp3"}, AIR),
    ("what did the welder think was causing the frame cracks", "own note", {A + "voice_note_frame_weld_cracks.mp3"}, WELD),
    ("what was the note about conveyor two jamming", "own note", {A + "voice_note_conveyor2_jam.mp3"}, CONV),
    # typed in Telugu (files are English, two voice notes Telugu)
    ("పంప్ ప్రెజర్ రావడం లేదు", "telugu", {D + "pump_troubleshooting_ufc.pdf#2", D + "pump_troubleshooting_ufc.pdf#1"}, PUMP),
    ("కంప్రెసర్ నుంచి గాలి లీక్ అవుతోంది", "telugu", {A + "voice_note_line2_air_leak.mp3", D + "compressed_air_maintenance_army.pdf#4", A + "air_leak_hiss.mp3"}, AIR),
    ("ప్యానెల్ మీద పని చేసే ముందు ఏం చేయాలి", "telugu", {D + "lockout_tagout_osha.pdf", D + "arc_flash_osha.pdf", A + "niosh_lockout_briefing.mp3"}, ELEC),
    ("ఫోర్క్‌లిఫ్ట్ బోల్తా పడింది", "telugu", {D + "forklift_safety_osha.pdf#1"}, FORK),
    ("పైప్ తుప్పు పట్టి సన్నబడింది", "telugu", {D + "pipe_corrosion_rupture_csb.pdf", D + "corrosion_protection_army.pdf"}, CORR),
    # spoken words inside a recording
    ("electricity powers our industries", "speech", {A + "niosh_arc_flash_briefing.mp3"}, ELEC),
    ("de-energize, lock out, and then verify", "speech", {A + "niosh_lockout_briefing.mp3"}, ELEC),
    ("arc flash is a danger that often goes unrecognized", "speech", {A + "niosh_arc_flash_briefing.mp3"}, ELEC),
    # only the picture can answer
    ("heat discoloration on a bearing shell after teardown", "visual", {I + "bearing_shell_overheat.jpg"}, PUMP),
    ("yellow danger padlocks on three isolator switches", "visual", {I + "lockout_padlocks_isolators.jpg"}, ELEC),
    ("worker putting on a full face arc flash hood", "visual", {I + "arc_flash_ppe.jpg"}, ELEC),
    ("exploded drawing of a pump with numbered parts", "visual", {D + "centrifugal_pump_manual_1946.pdf#2", D + "centrifugal_pump_manual_1946.pdf#3"}, PUMP),
    ("cut pipe sample showing a thin wall next to a thick wall", "visual", {D + "pipe_corrosion_rupture_csb.pdf#4"}, CORR),
    ("camera that shows gas leaking from a compressor", "visual", {V + "compressor_gas_leak_camera.mp4"}, CORR),
    ("coal moving underground on a long belt", "visual", {V + "belt_conveyor_coal.mp4"}, CONV),
    ("instructor teaching someone to drive a forklift", "visual", {V + "forklift_training.mp4"}, FORK),
    ("machine shop lathe cutting metal", "visual", LATHE, LATHE),
]


def ok_first(r, top):
    return r["file"] in top or (r["kind"] == "doc" and f"{r['file']}#{r.get('page', 1)}" in top)


def file_ok(r, top):
    return r["file"] in {t.split("#")[0] for t in top}


def mmss(t):
    return f"{int(t) // 60}:{int(t) % 60:02d}"


def label(r):
    w = f" p{r['page']}" if r["kind"] == "doc" else f" @{mmss(r['start'])}" if r["kind"] in ("audio", "video") else ""
    return f"{r['file'].split('/')[1].rsplit('.', 1)[0]}{w}"


if __name__ == "__main__":
    out, tally = [], {}
    for q, kind, top, group in QS:
        res = search(q, k=12)["results"]
        first = res[0]
        exact, right_file = ok_first(first, top), file_ok(first, top)
        top4 = res[:4]
        rel = [r for r in top4 if r["file"] in group]
        kinds = len({r["kind"] for r in rel})
        score = 3 * exact + 1 * (right_file and not exact) + len(rel) + kinds
        t = tally.setdefault(kind, [0, 0])
        t[0] += exact
        t[1] += 1
        mark = "EXACT" if exact else ("file" if right_file else "MISS")
        out.append((score, q, kind, mark, len(rel), kinds, [label(r) + f" {r['score']:.2f}" for r in top4]))
        print(f"{mark:5} {len(rel)}/4 {kinds}k s{score:<2} [{kind:8}] {q[:70]:70} | {' ; '.join(label(r) for r in top4)}")
    print("\nby kind:", {k: f"{a}/{b}" for k, (a, b) in tally.items()})
    total = sum(a for a, _ in tally.values())
    print(f"exact first: {total}/{len(QS)}")

    md = ["# Hard questions on the plant library (2026-10-14)", "",
          f"40 questions written before running. Exact first: **{total}/{len(QS)}**. By kind: "
          + ", ".join(f"{k} {a}/{b}" for k, (a, b) in tally.items()) + ".", "",
          "EXACT = right file (and page) first. file = right file, other page. Rel = relevant results in the top 4. Types = file types among those.", "",
          "| Score | Result | Rel | Types | Kind | Question | Top 4 |", "|---|---|---|---|---|---|---|"]
    for s, q, kind, mark, rel, kinds, t4 in sorted(out, key=lambda x: -x[0]):
        md.append(f"| {s} | {mark} | {rel}/4 | {kinds} | {kind} | {q} | {'; '.join(t4)} |")
    (ROOT / "HARD-QUESTIONS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
