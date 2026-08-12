# YouTube Novel Studio — Final Pipeline

## Goal
The user supplies only the work/episode direction. The system produces a reviewable private YouTube-ready episode while preserving story quality.

## Production stages
1. STORY LOAD — load canon, character rules, prior episode summary and current outline.
2. EPISODE PLAN — split the episode into scenes and define purpose, hook, mood and speakers.
3. DRAFT — write scenes independently to avoid short-output failure.
4. LENGTH GATE — count real characters and estimate narration duration; expand only scenes that need it.
5. CONTINUITY GATE — check canon, character voice, chronology, repeated exposition and unresolved setup.
6. AUDIO SCRIPT — convert prose to narrator/dialogue/pause/SFX/BGM cues.
7. VOICE — generate narrator and character tracks; insert directed pauses.
8. SOUND DESIGN — select BGM by scene mood, duck music under speech, place sparse event-based SFX.
9. VISUAL DIRECTION — choose available work assets and apply pan/zoom/crop/fade/flash/shake rules rather than static display.
10. SUBTITLES — generate timed cinematic subtitles.
11. RENDER — create final 1080p MP4 and QC metadata.
12. QC — verify duration, missing audio, subtitle presence, render success and metadata.
13. YOUTUBE — upload as PRIVATE only.
14. HUMAN APPROVAL — public release remains manual until the system proves stable.

## Episode source format
Each episode will ultimately have structured scene data containing:
- scene id
- prose/dialogue
- speaker
- mood
- pause cues
- BGM cue
- SFX cue
- visual asset cue
- camera/motion cue

## Non-negotiable rules
- Existing `mongyeong` VN repository is never modified by this studio.
- Story quality takes priority over exact runtime.
- Runtime target is a range, not padding.
- Do not invent canon to fill length.
- Do not publish publicly without approval.
- Missing optional BGM/SFX/assets must not prevent a basic render; the QC report must flag omissions.

## Build order
Phase A: structured episode + quality gates
Phase B: multi-voice + pause direction
Phase C: BGM/SFX mixer
Phase D: visual motion director
Phase E: metadata/thumbnail package
Phase F: private YouTube uploader + approval gate
