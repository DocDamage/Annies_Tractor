# Running on a 12 GB GPU

afv was developed on a 16 GB RTX 5080. These are measurements from an RTX 3060 with 12 GB (compute capability
8.6, driver with CUDA 13.3, WSL2 Ubuntu 24.04, about 23 GB RAM in WSL), taken on 2026-11-16 and 2026-11-17 with
the installers as fixed in PR #1. Short version: the whole pipeline runs, ViPE included, but the camera stage
leaves little room on 12 GB.

## Peak GPU memory per stage

Measured with [`tools/gpu_profile.py`](../tools/gpu_profile.py): total memory in use on the GPU, sampled five
times a second, and the same minus what was in use before the run (the Windows desktop).

Shot 1: an 8 s handheld street clip, two people, 242 frames at 30 fps.

| Stage | Time | Peak total | Above the desktop (1.0 GB) |
| --- | --- | --- | --- |
| detect_track (RF-DETR + SAM 2.1) | 127 s | 2.9 GB | 1.8 GB |
| camera, `vipe` | 351 s | 11.0 GB | 9.9 GB |
| camera, `background` | 29 s | 1.8 GB | 0.8 GB (GeoCalib) |
| pose3d (GEM-X) | 120–150 s | 4.8 GB | 3.8 GB |
| pair, contacts, smooth, hands_face, export | under 2 s each | none | none |

Shot 2: a 7.5 s broadcast boxing shot, wide side view of two fighters, 225 frames at 30 fps.

| Stage | Time | Peak total | Above the desktop (1.3 GB) |
| --- | --- | --- | --- |
| detect_track | 137 s | 3.2 GB | 1.9 GB |
| camera, `vipe` | 151 s | **11.7 GB** | 10.4 GB |
| pose3d | 128 s | 4.8 GB | 3.5 GB |

Neither ViPE run hit an out-of-memory error, a retry or a lower resolution. ViPE's peak depends on the shot, not
only its length: the shorter shot 2 needed 0.7 GB more than shot 1.

## What this means on 12 GB

- **ViPE fits, with about 0.3 GB to spare on shot 2.** Close everything else that uses the GPU while it runs:
  games, video in a browser, local language models (Ollama, LM Studio). The desktop alone took 1.0–1.3 GB.
- **If the camera stage runs out of memory,** use `afv run <shot> --camera background`: it peaked at 1.8 GB here,
  so the pipeline's peak drops to GEM-X's 4.8 GB. It is less robust than ViPE (P0_FINDINGS: it lost the camera
  on 2 of 8 solves), so keep ViPE when it fits.
- **detect_track and pose3d** never came near the limit.
- A 3060 is slower than a 5080: about 8–11 minutes per shot end to end with ViPE.

## Measuring your own GPU

From a project folder in WSL (stages already up to date are skipped, so force the ones to measure):

```bash
python /mnt/d/afv/tools/gpu_profile.py 004 --from detect_track --camera vipe --yes
python /mnt/d/afv/tools/gpu_profile.py 004 --from camera --camera background --yes --json background.json
```

It prints each stage's time and peak memory; `--json` also writes them to a file.

## Notes from the install on this machine

The three install problems met here are fixed in the installers (PR #1, see the troubleshooting table in
`HOLD_MY_HAND.md`): uv's download timeout, ViPE's and SAM 2's CUDA builds on the system Python, and the static
ffmpeg 7.0.2 being skipped when Ubuntu has its own ffmpeg. The ViPE CUDA build for compute capability 8.6 worked
as written.
