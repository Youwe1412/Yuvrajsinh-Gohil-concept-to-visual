# Footage inventory

Before planning a single graphic, know everything Joel has already provided. Joel prefers his own
footage and real captures over anything generated (rule J-01), offers to film specific shots on
request, and sends footage in batches (Frame.io downloads). In P1, 20 of his 66 Frame.io notes were
answered by footage already in hand or delivered later, not by a build.

## Procedure

1. **Find every candidate file.** The project's footage folders (P1 used `Broll/`; P2 used
   `Videos and Media/`), Frame.io download batches and their logs, `assets/` or `media/` folders, and
   anything Yuvraj names. Ignore exports we made (rough cuts, renders, review proxies) unless Yuvraj
   says otherwise; list them separately.
2. **Read the specs** with `ffprobe` for each file: duration, resolution, frame rate, codec, alpha,
   audio present or not, and (for images) pixel size.
3. **See what it shows.** Make a contact sheet per clip (one frame every few seconds, timecodes burned
   in) and look at it. Describe the content in plain words: what is on screen, what happens, any
   readable text or UI.
4. **Flag problems:** wrong or variable frame rate, vertical or odd aspect, low resolution for a
   full-frame use, baked-in UI or sidebars (P1's `AIResponseToBuild` had a white sidebar that needed
   a reframed copy), private information on screen, watermarks, shaky or soft focus.
5. **Match it to the words.** For each file, list the transcript lines or word IDs it could serve, and
   whether it is **evidence** (it proves or shows the actual thing) or **atmosphere** (it sets a
   mood). Evidence footage is used as it is, never upscaled with an AI tool or redrawn.
6. **Note the gaps.** Moments that need footage Joel hasn't supplied become either a code-rendered
   graphic or a shot request for Joel ("shots to ask him to film" in `visual-plan.md`).

## Write `footage-inventory.md`

| File | Duration | Res · fps | Audio | Shows | Problems | Could serve (word IDs / lines) | Evidence or atmosphere |
|---|---|---|---|---|---|---|---|

Keep the contact sheets in `reviews/footage/`. Re-run when a new batch arrives, and note the batch
date at the top of the file.
