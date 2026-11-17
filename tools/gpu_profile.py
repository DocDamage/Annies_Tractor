"""Peak GPU memory per pipeline stage for one shot.

Runs ``afv run SHOT [afv run options]`` in the current project folder (inside WSL) while sampling the
GPU's used memory with ``nvidia-smi`` five times a second, then prints each stage's time and peak memory,
in total and above what was in use before the run started (the desktop and anything else on the GPU).
Stages already up to date are not re-run, so use ``--from detect_track`` (or ``--camera ...`` on a new
camera mode) to measure them.

Usage, from a project folder:

    python /mnt/d/afv/tools/gpu_profile.py 004 --camera vipe --yes
    python /mnt/d/afv/tools/gpu_profile.py 004 --from camera --camera background --yes --json peaks.json

The afv command is ``$AFV`` if set, else ``~/afv/afv-env/bin/afv``. This file imports nothing from afv, so any
Python 3.11+ runs it. It holds no GPU lock of its own; ``afv run`` takes the lock for each GPU stage as usual.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

STAGE_LINE = re.compile(r"^\s+(\w+)\s+(running|done in|FAILED)")
BASELINE_SECONDS = 5.0
SAMPLE_MS = 200


@dataclass
class Sampler:
    """Reads ``nvidia-smi`` in a thread: (monotonic time, MiB used) per sample."""

    samples: list[tuple[float, int]] = field(default_factory=list)
    proc: subprocess.Popen[str] | None = None

    def start(self) -> None:
        self.proc = subprocess.Popen(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits", f"-lms={SAMPLE_MS}"],
            stdout=subprocess.PIPE,
            text=True,
        )
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        for line in self.proc.stdout:
            try:
                self.samples.append((time.monotonic(), int(line.split(",")[0])))
            except ValueError:
                continue

    def stop(self) -> None:
        if self.proc is not None:
            self.proc.terminate()
            self.proc.wait(timeout=10)

    def peak(self, start: float, end: float) -> int:
        return max((mib for t, mib in self.samples if start <= t <= end), default=0)


@dataclass
class Stage:
    name: str
    start: float
    end: float | None = None
    failed: bool = False


def run(shot: str, afv_args: list[str]) -> tuple[int, list[Stage], Sampler, int]:
    afv = os.environ.get("AFV", str(Path.home() / "afv/afv-env/bin/afv"))
    sampler = Sampler()
    sampler.start()
    time.sleep(BASELINE_SECONDS)
    before = sorted(mib for _, mib in sampler.samples)
    baseline = before[len(before) // 2] if before else 0
    stages: list[Stage] = []
    open_: dict[str, Stage] = {}
    proc = subprocess.Popen(
        [afv, "run", shot, *afv_args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        now = time.monotonic()
        m = STAGE_LINE.match(line)
        if not m:
            continue
        name, what = m.groups()
        if what == "running":
            open_[name] = Stage(name, now)
            stages.append(open_[name])
        elif name in open_:
            stage = open_.pop(name)
            stage.end, stage.failed = now, what == "FAILED"
    code = proc.wait()
    time.sleep(2 * SAMPLE_MS / 1000)
    sampler.stop()
    return code, stages, sampler, baseline


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("shot", help="shot id, e.g. 004")
    parser.add_argument("--json", type=Path, help="also write the table here")
    args, afv_args = parser.parse_known_args()
    code, stages, sampler, baseline = run(args.shot, afv_args)
    gib = 1024.0
    rows = []
    print(f"\nbefore the run: {baseline / gib:.2f} GB in use, {len(sampler.samples)} samples")
    print(f"{'stage':<13} {'seconds':>8} {'peak GB':>8} {'above GB':>9}")
    for s in stages:
        end = s.end if s.end is not None else time.monotonic()
        peak = sampler.peak(s.start, end)
        above = max(peak - baseline, 0)
        state = " FAILED" if s.failed else ("" if s.end is not None else " (unfinished)")
        print(f"{s.name:<13} {end - s.start:8.1f} {peak / gib:8.2f} {above / gib:9.2f}{state}")
        rows.append(
            {
                "stage": s.name,
                "seconds": round(end - s.start, 1),
                "peak_gb": round(peak / gib, 2),
                "above_baseline_gb": round(above / gib, 2),
                "failed": s.failed,
            }
        )
    overall = max((mib for _, mib in sampler.samples), default=0)
    print(f"overall peak {overall / gib:.2f} GB")
    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "shot": args.shot,
                    "afv_args": afv_args,
                    "baseline_gb": round(baseline / gib, 2),
                    "overall_peak_gb": round(overall / gib, 2),
                    "stages": rows,
                },
                indent=2,
            )
        )
    return code


if __name__ == "__main__":
    sys.exit(main())
