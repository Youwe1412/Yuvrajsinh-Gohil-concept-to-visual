# Word timing: the word map

Rule M-03: the readable pose lands on the stressed word; GSAP labels are keyed to word IDs; offsets
are measured in frames. This file is how to get times good enough for that.

## Why it is done this way

- **Two problems, two tools.** *Recognition* (which words) and *alignment* (exactly when each starts)
  are different jobs. Speech-to-text models are built for the first and only approximate the second.
  Forced alignment against known text is built for the second: Montreal Forced Aligner placed 89% of
  word boundaries within 50 ms on read speech, WhisperX 82% (Rousso et al., Interspeech 2024).
- **The target is one frame of this edit.** A frame lasts `fps_den / fps_num` seconds: about 41.7 ms
  in a 23.976 edit (P1, 24000/1001) and 40 ms in a 25 fps edit (P2, 25/1). P1's word times came from
  whisper.cpp small.en token timestamps and drifted by up to 0.19 s (4–5 frames) around 08:05; that
  shot had to be timed by measuring breath gaps on the waveform by hand (P1 `OUTSTANDING.md`).
- **Time is timeline time.** Times must come from the audio of the cut the graphics will sit in.
  A re-cut moves every word after the edit point.
- **Claude cannot hear.** "Accurate" is proved with numbers (aligner confidence, waveform onsets) and
  a human scrub of anything uncertain, never asserted.
- **The best local model changes.** Check what is installed at the start of every project; don't
  trust a name written here.

## Frame rate: record it once, as a rational

At G1, read the edit's exact rate from the timeline itself (the FCPXML sequence format's
`frameDuration`, e.g. `1001/24000s` or `1/25s`), not from a file name or a rounded number. Store it
as two integers, `fps_num` and `fps_den` (P1's frameDuration `1001/24000s` → 24000/1001; P2's
`1/25s` → 25/1). Use them for every conversion in the project:

```
frame = round(seconds × fps_num / fps_den)
```

Examples: P1 was 24000/1001 (23.976). P2's timeline in Cut Assist reads `frameDuration 1/25`, so
25/1. Confirm each new video; never carry a rate over from the last one.

## Procedure

0. **Use Cut Assist's alignment if the cut was cleaned there.** Aavkar Cut Assist
   (`~/Documents/Aavkar Cut Assist`) runs WhisperX-aligned word timings on the raw footage when it
   prepares the V1 cleanup. If this video went through it, start from those times.
   - **List the MCP's tools first** and use the names it reports; don't guess. As of 6 October 2026
     they include `studio_connection_status`, `studio_projects`, `studio_context`, `studio_evidence`
     (transcripts, alignment, timing guards per analysis window), `studio_transcript_mapping` (word
     indices, `mapping_hash`, unsafe words) and `studio_pause_map` (source and edit times). Confirm
     with `studio_connection_status`, find the project with `studio_projects`, and read
     `studio_context` for its jobs, timeline format and accepted cuts.
   - **Read only.** This skill reads timings; it never submits cleanup proposals or task results,
     and it never touches a project whose AI permission isn't recorded or a protected historical
     project (Cut Assist's own rules).
   - **Map to timeline time.** Cut Assist's word times are in source-media time, per analysis
     window (add the window's `source_start_seconds`). Map each word through the cut's edits (the
     current FCPXML: each clip's `offset`, `start` and `duration`) to timeline time. A word that
     falls in removed material has no timeline time; drop it. If the current cut has moved on from
     the Cut Assist revision, map through the current FCPXML, not Cut Assist's plan.
   - **Keep the cross-reference.** Store Cut Assist's word index, job ID, window and `mapping_hash`
     beside our `w` ID in `words.json`.
   - **Skip words Cut Assist marks unsafe or blocked** for timing; treat them as unaligned.
   - Then go to step 3 (settle the wording) and step 6. Step 6's waveform check still applies to
     every cue word. Use MFA (step 4) only for words that fail that check, or for the whole video
     when Cut Assist doesn't have this cut.
1. **Export the audio of the current cut** from Final Cut (or take it from the supplied video with
   ffmpeg): 48 kHz mono WAV. Record its SHA-256, the timeline or file name and version, and
   `fps_num`/`fps_den`. If only Joel's raw recording exists, say so: times will need remapping
   after the cut.
2. **Recognise the words** with the most accurate local engine available. Check in this order and
   use the first that works:
   - Parakeet through HyperFrames: `hyperframes transcribe <audio> --engine parakeet --json`
     (install once with `hyperframes models install parakeet`). Cut Assist's runtime
     (`~/Tools/fcp-edit-workflow`) also has Parakeet TDT, Whisper large-v3 and WhisperX installed.
   - whisper.cpp with `large-v3` (`whisper-cli`, or `hyperframes transcribe --engine whisper -m large-v3`).
   - whisper `small.en` only as a last resort.

   This draft is good enough for planning (G1–G2), not for final cue times.
3. **Settle the wording.** Compare the draft with Joel's script. Joel's spoken words win; the script
   fixes spellings of names, products and terms. Where he went off-script, keep what he said. Save
   the corrected text as `data/transcript-final.txt`.
4. **Align** the corrected text to the audio with Montreal Forced Aligner (English MFA acoustic model
   and dictionary; add unknown terms such as product names to the dictionary). Output: start and end
   per word and phone. When step 0 supplied the times, align only the words that failed step 6.
5. **Number and convert.** Give every word a stable ID `w0…wN` in order. Convert times to frames with
   the edit's rate: `frame = round(seconds × fps_num / fps_den)`.
6. **Verify the cue words.** For every word that will drive a cue (stressed words, list items,
   numbers), check its onset against the waveform: an energy onset within ±1 frame of the aligned
   start passes. List failures and low-confidence words for a human scrub; never guess them.
7. **Write `data/words.json`:** `fps_num`, `fps_den`, the words with IDs, start/end in seconds and
   frames, confidence, the source of each time (Cut Assist, MFA, or recogniser only) with any Cut
   Assist cross-reference, the audio SHA-256, the timeline version, the engines and model versions
   used, and the verification result. Keep the engine's raw output beside it.

## When MFA isn't available

Use Cut Assist's aligned times if step 0 applies; otherwise the recognition engine's word times. Mark
the unaligned words in `words.json` as **"unaligned, about ±200 ms"**, and make step 6 mandatory for
every cue word, not just a sample. Tell Yuvraj that alignment was skipped.

## When the cut changes

Re-run from step 0 or 1. Because GSAP labels are keyed to word IDs, a re-alignment moves the
animation with the voice; only labels whose words changed need attention.
