# Roadmap

This is a list of suggested work, written after a review of the repository on 2026-11-17. It sits alongside
"Open for round 7" in [ROUND6_NOTES.md](ROUND6_NOTES.md) and repeats the most important items from it.
Nothing here is built yet unless it is ticked.

Priority: **P1** do next · **P2** worth doing soon · **P3** later or nice to have.
Effort: **S** about a day · **M** a few days · **L** a week or more.

---

## Part 1: Fix, harden and maintain

### Fix what's already broken
- [ ] **P1 · M — A take imported inside the shot browser's own .blend doesn't play.** The skeletons show
  but don't move when scrubbing or playing. The notes suspect the timeline is driving the browser's scene
  instead of the take's scene (Blender 5's sequencer-scene time sync), or the browser's handlers (frame
  change, undo re-sync, Loop shot preview range). Fix it together with a windowed test that plays a real
  take in the browser's file. Details: ROUND6_NOTES.md, "Open for round 7".
- [ ] **P2 · S — Lock files.** They pile up in `~/afv/locks` (`shots-*`, `shotinfo-*`, `batch-*`), and
  `tests/media` and `tests/serve` write there too. Two batch starts at once can both try to take the lock,
  and the GPU-wait message can name a holder that has already gone. Fixes: give tests their own lock
  folder, take locks atomically, remove locks whose process has gone, and add a finish time to
  `batch_status`.

### Make installs reproducible
- [ ] **P1 · S — Pin the model code in the installers.** `install_gemx.sh`, `install_vipe.sh` and
  `install_track.sh` clone the newest GEM-X, ViPE and SAM 2 and only afterwards record what they got in
  `install/tested_versions/`. By default, check out the commits recorded there; add an opt-in `--latest`
  flag for the old behaviour. Pin the pip packages (`torch`, `rfdetr`, …) to the tested versions too.
- [ ] **P2 · S — One version number.** `pyproject.toml` and `src/afv/__init__.py` say 0.1.0, while
  `blender/afv_addon/blender_manifest.toml` says 0.2.0. Keep a single version, and have `afv serve` and
  the add-on check each other's version when they connect, so a mismatch shows a clear message.

### Catch problems automatically
- [x] **P1 · S — CI.** `.github/workflows/ci.yml` runs `ruff` and the CPU test suite on every push and
  pull request. GPU and Blender tests are left out (they need the author's machine); tests that need
  footage-derived fixtures skip as they do locally.
- [ ] **P3 · S — Blender tests in CI.** Download Blender 5.2 in the workflow and run the
  `blender`-marked tests headless.
- [ ] **P2 · M — Split the largest modules.** `motion/contacts.py` (~2,400 lines), `cli.py` (~2,300),
  `blender/afv_addon/retarget.py` (~2,000), `models/camera.py`, `core/runner.py`, `models/gemx.py`,
  `models/track.py` and `serve.py` (1,500–1,900 each). Splitting `cli.py` into one module per command
  group is the easiest start.

### Known quality issues (from the round notes)
- [ ] **P2 · M — Cut detection.** Some hard cuts are found 1–3 frames late, some are false (a light flare
  at frame 15800 of Full Fight), there's no progress while it runs, and `duration` is stored with float
  noise.
- [ ] **P2 · M — `fighters_likely`.** It misses clinches (detected as one box) and marks walkouts and
  corner shots as fights.
- [ ] **P3 · M — Motion carry-overs from rounds 4–5.** Plant-edge flips (~1.5 cm root path), the
  close_boxing A right heel plant floats 2 cm, GEM-X depth drift in `pair.distance_median_m`, adjacent
  opposite pins overshoot.
- [ ] **P2 · S — End-to-end checks not yet done.** A real overnight batch through to export from the
  browser; File > Revert during a batch; "Pick on this frame" on the GPU; Windows sleep or WSL shutdown
  during a long batch; the keyboard shortcuts in a real session.

### Small cleanups
- [ ] **P3 · S — Tidy the repo.**
  - Remove `Init design doc.pdf` (7.8 MB), move it under `docs/`, or store it with Git LFS. It
    duplicates `docs/SPEC.md`.
  - Move the README's "Just setting things up" line and donate button from the top to the end.

---

## Part 2: New features and better functions

### Turning takes into game-ready moves
A game needs separate moves ("jab", "slip left", "hit react"), but the pipeline gives you whole shots.

- [ ] **P1 · M — Strike detection and auto-clipping.** The smoothing stage already detects strikes so it
  can keep impacts sharp (`motion/smooth.py`, `motion/ik.py`; labels in `qc/labels.py`). Use that data to
  mark each punch or kick on the timeline with its wind-up, impact and recovery, then add a **clip
  cutter** that splits a take into named moves, each exported as its own animation. Needs: a clips edit
  file (`shots/<id>/edits/clips.json`, validated like the other edits), a Blender panel to adjust clip
  edges, and export of one action per clip.
- [ ] **P1 · M — Move library.** A searchable catalogue of every clip across all projects: move type,
  fighter, source shot, quality score and a thumbnail or GIF preview. Filtering it ("all left hooks with a
  quality score above 0.8") turns a pile of footage into an animation library. Start with
  `afv library list/search --json` and a Blender panel on top of it.
- [ ] **P2 · M — Attack and reaction pairs.** Both fighters are already solved in one shared world. Export
  a clip that covers the strike and the opponent's reaction as a matched pair of animations, keeping their
  spacing and timing, so the game can play them in sync.

### Cleanup tools that save the most time
- [ ] **P1 · S — Mirror a take.** Turn a right-handed jab into a left-handed one (orthodox to southpaw),
  which doubles the useful output of every take. Swap left and right joints by name, reflect the
  rotations and the root path, and add it as an `afv take --mirror` option and a Blender button.
- [ ] **P2 · M — Loop and blend helper** (FR-20 in the spec). Find the best loop point in a footwork or
  guard idle and blend the seam, so stance cycles become seamless idles and walk cycles.
- [ ] **P3 · M — Blend between clips.** Join the end of one move to the start of another, for building
  combos or checking how moves flow into each other.
- [ ] **P2 · S — Confidence-guided review.** Rank frames by quality (tracking hints, how far the solved
  joints project from where the video shows them, foot slide, confidence) and jump straight to the worst
  stretch with "Next problem" / "Previous problem" in the cleanup panel.

### Better results from the footage
- [ ] **P2 · L — Clinch handling, first step** (towards FR-21). Detect when the two fighters merge into one
  box, mark those frames as low-confidence, and fill the gap by blending between the good frames on either
  side instead of letting the motion jump.
- [ ] **P3 · L — Linking a fighter across shots** (backlog in the spec). Match the same fighter's
  appearance across camera cuts, so motions from several shots are tagged "this is fighter X" and can be
  gathered into one character's moveset.
- [ ] **P3 · M — Detect slow motion automatically.** Retiming works (`motion/retime.py`), but the speed
  factor is set by hand. Detect replays (the graphic wipe that starts them, frame-rate signatures,
  unusually slow motion) and suggest a speed factor.

### Engine export
These build on the planned engine-ready export work (root motion, engine presets, real-world size, batch
retarget, an automated import check). The owner should choose which engine comes first.

- [ ] **P2 · S — Animation events in exported files.** Write impact frames, foot plants and the moment a
  hit lands as markers or notifies in FBX and GLB. Game engines can use them for hit detection, sounds
  and particle effects without anyone marking them by hand.
- [ ] **P3 · M — Hit volumes.** Export the frames where a glove or foot meets the opponent and how much
  they overlap. The code that keeps the two bodies from passing through each other already computes this
  (`capsule_penetration` in `motion/pair.py`).
- [ ] **P2 · M — Engine-specific export settings.** Unity Humanoid avatar settings, Unreal's skeleton
  naming and Godot's import settings as one-click choices, on top of `export/presets.py`.

### Pipeline quality of life
- [ ] **P2 · M — Batch dashboard in Blender.** Per-shot progress, time remaining, which GPU stage is
  running, and a list of failed shots with their reasons, so an overnight run is easy to check in the
  morning.
- [ ] **P3 · M — Before/after compare.** Show two results of the same shot side by side, before and after
  a fix or between settings, with the quality numbers next to them.

---

## Suggested order
1. Fix the playback bug, pin the installers and add CI (done) — keeps the base dependable.
2. Mirror a take, strike detection with auto-clipping, and the move library — the most usable animation
   for the least effort, built on data the pipeline already produces.
3. Engine-ready export with animation events, then the engine-specific settings.
4. Confidence-guided review, the loop and blend helper, and the batch dashboard.
5. Clinch handling, linking fighters across shots, and detecting slow motion automatically.
