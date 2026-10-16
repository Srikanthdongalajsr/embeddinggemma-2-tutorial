# Plant library: what works, what doesn't (2026-10-14)

50 public files (18 photos, 12 sounds, 9 videos, 11 manual and safety documents), indexed with EmbeddingGemma 2 (207 vectors). The queries were written before indexing (`QUERIES-before-results.md`); the tests are in `app/plant_eval.py`.

## The pain this answers

A machine stops at 2 AM. The technician on shift has never seen this fault. What the plant knows about it is spread over a manual page, a teardown photo, a recording and a video, and the person who fixed it last time has left. One search box over all of it, running inside the plant, cuts the time spent hunting and keeps that knowledge after people leave.

## Results

**Symptom search: one sentence, the best file of each type (16 of 24 right)**

| Symptom typed | Manual page | Photo | Sound | Video |
|---|---|---|---|---|
| electrician needs to work on the panel, is switching it off enough | OK: OSHA arc flash | OK: breaker locked and tagged | OK: NIOSH lockout briefing | OK: arc flash clip |
| air pressure keeps dropping on the line and we can hear hissing | OK: Army compressed-air maintenance (leaking joints table) | OK: air compressor | OK: air hiss | wrong: arc flash (matched on its hissing sound) |
| old pipe is thinning and started dripping under the insulation | OK: CSB Chevron pipe rupture report | OK: rusted valve | OK: air hiss | wrong: CNC lathe |
| pump is vibrating badly and the bearing housing is getting hot | OK: DoD pump troubleshooting ("pump vibrates or is noisy") | OK: belt-driven pump | wrong: welding | wrong: compressor leak camera |
| operator's hand got caught clearing a jam on the conveyor | OK: OSHA conveyor guarding | OK: conveyor line | wrong: forklift | wrong: butt welding |
| new welds on the frame are cracking | OK: Army weld defects page | wrong: welding photo, not the crack | OK: MIG welding | wrong: arc flash |

**Short queries: 10 of 16 put a right file first.**
- **Manual pages are the strongest:** pump noise, lockout steps and welding fumes all come first, at the right page.
- **Photos are strong:** rusted flange, padlocks on switches, sparks, conveyor.
- **Sounds described in words are weak:** "loud air compressor running" puts the compressor 5th. This matches the first library, where music by description was also the weak spot.

**Telugu (typed in Telugu, files in English): 2 of 3 first, the third 2nd.** "వెల్డింగ్ పొగ" (welding smoke) finds the OSHA welding fumes sheet. "కన్వేయర్ జామ్ అయింది" (conveyor jammed) finds the conveyor guarding page. "పంప్ నుంచి చాలా శబ్దం వస్తోంది" (lots of noise from the pump) puts the pump troubleshooting page 2nd, behind the conveyor page.

**Healthy vs faulty pump: it can't tell them apart.** The two recordings score 0.895 similar. Even "a pump running normally" scores the faulty one higher. **Never claim fault detection.**

**Speed:** about 45 ms per search on the GPU and 135 to 170 ms on the CPU alone (text-only model, 50 files).

**Grouping: weaker than search, so don't make it a main claim.**
- **Raw:** it groups by file type again. Only 1 of 6 groups mixes types (same file-type pull as the first library).
- **After removing each type's average:** 5 of 6 groups mix types, but topic purity is only 0.48. The groups are broad themes, not clean topics:
  - Safety procedures: lockout and arc flash documents, the NIOSH briefings, lockout photos, and forklift safety and training.
  - Machines running: compressor, conveyor, forklift and grinder sounds with the conveyor, compressor and hydraulic videos.
  - Pipework and pumps: the pump manuals, rusted valves, the corroded-pipe report and the pump photo.
  - Hot work and hiss: weld documents, welding photos, the hiss sounds and rust.
- **Honest line for the video:** "it sorts a pile of plant files into broad themes, like safety procedures and machines running, without any labels."

## Technician voice notes (yours, staged; added 2026-10-14)

There are 4 notes from `self-audio/`: pump 3 and frame welds in Telugu, line 2 air leak and conveyor 2 jam in English. They're indexed as audio. No transcript is made anywhere.

**Typed query → the right note: 7 of 10 first; the other 3 are 2nd, each behind the matching manual page.**
- "grinding noise from pump 3, bearing hot" finds the Telugu pump note first (0.80).
- "weld cracks on the frame" finds the Telugu weld note first (0.78). This is English text finding Telugu speech.
- "పంప్ బేరింగ్ వేడిగా ఉంది" (pump bearing is hot, typed in Telugu) finds the Telugu pump note first.
- "pressure dropping on line two, hissing from a joint" finds the English air-leak note first.
- The conveyor note comes 2nd, behind the OSHA conveyor guarding page.

**The symptom searches now return the plant's own experience:**
- **"pump is vibrating badly and the bearing housing is getting hot":** 1. DoD pump troubleshooting page, 2. your Telugu note ("same thing last time, we changed the bearing"), 3. the 1946 pump manual.
- **"air pressure keeps dropping on the line and we can hear hissing":** 1. your line 2 note, 2. the Army leaking-joints table, then the hiss recording.
- **"new welds on the frame are cracking":** 1. your Telugu weld note, 2. the Army weld defects page.

**Caveat:** the line 2 note also comes up for loosely related faults (it tops "old pipe dripping under insulation"). Notes that talk about leaks attract leak-like queries. That's expected, and fine to show.

**Assumption to check by ear:** `script2_3_4_mix.aac` was cut at its two pauses, assumed to be in script order (air leak, welds, conveyor). The search results support it, since "weld cracks" finds the 5.8 s middle part.

## Updated main shot

**"pump is vibrating badly and the bearing housing is getting hot"**: the manual page answers "what could cause it", and the senior technician's Telugu note answers "what fixed it here last time". That's the knowledge-loss pain, solved in one search.

## Not tested (no matching open file)

There's no oil-leak photo, no frayed conveyor belt photo and no reverse beeper. Commons has nothing usable for any of them.

## Recommended main shots

1. **"air pressure keeps dropping on the line and we can hear hissing"**, with One of each turned on. It returns the leaking-joints maintenance table, the hiss, and the compressor. Once your English voice note on line 2 is in, it should come back too. That's a real fault, answered from four kinds of files.
2. **"electrician needs to work on the panel, is switching it off enough"**: 4 of 4 right, with a spoken NIOSH answer.
3. **Live Record note:** record a note on camera, then search for it seconds later. This proves nothing is pre-staged.
4. **A Telugu query finding an English manual page** ("వెల్డింగ్ పొగ").

Avoid these on camera: pump sound search, healthy-vs-faulty, and grouping as a "trends" claim.
