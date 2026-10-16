# Plant demo queries (written 2026-10-14, before any file was indexed)

Written first so the test can't be tuned to the results. Expected files are filled in once the library is fixed, still before indexing.

Main queries (things text search can't reach):
- rusted pipe flange (photo)
- a cracked weld (photo)
- oil leaking from a machine (photo)
- padlock and tag on an electrical switch (photo)
- damaged bearing (photo)
- frayed conveyor belt (photo)
- forklift moving pallets in a warehouse (video)
- sparks flying from welding (video)
- boxes moving on a conveyor (video)
- hissing sound of an air leak (audio)
- loud air compressor running (audio)
- beeping of a reversing forklift (audio)

Supporting queries (manual pages):
- pump is noisy and vibrating, what could be the cause
- steps to lock out a machine before maintenance
- how to stay safe from welding fumes

Language test (claim nothing until it passes):
- पंप से बहुत आवाज़ आ रही है (Hindi: "the pump is making a lot of noise")
- वेल्डिंग का धुआं (Hindi: "welding fumes")

Extra tests:
- Do normal and faulty machine sounds land apart? (only if paired sounds are found)
- Search time on CPU only.

## Expected files (fixed after download, before the index finished)

The full mapping is in `app/plant_eval.py` (CASES). Two frozen queries have no matching file, because Commons has no usable open photo of an oil leak or a frayed conveyor belt: "oil leaking from a machine" and "frayed conveyor belt". They're reported as untestable, not dropped silently. "beeping of a reversing forklift" has no beeper in the library either, so the forklift recording counts as the right answer.

## Language change (2026-10-14, after the first eval run)

The user speaks English and Telugu, not Hindi. The two Hindi queries were replaced with Telugu ones (pump noise, welding smoke, conveyor jam). The Hindi results from the first run are kept in the eval notes for the record.
