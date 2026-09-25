#!/usr/bin/env python3
"""
=====================================================================
 setup_assets.py -- iTantra Neural Transceiver | Sender-Side Assets
=====================================================================

Purpose
-------
Provisions the two ONNX model bundles required by `main_sender.py`:

    1. Silero VAD      -> Voice Activity Detection (gates the mic
                           stream so STT only runs on actual speech).
    2. Sherpa-ONNX STT -> A streaming Zipformer transducer
                           (encoder / decoder / joiner) for fully
                           offline speech-to-text.

Both are pulled directly from their official upstream repositories --
no mirrors, no placeholder URLs. See "MODEL NOTES" below for why this
specific STT checkpoint was chosen over the more commonly-referenced
one.

Design constraints honoured
----------------------------
  * Zero third-party pip dependencies (stdlib only).
  * Idempotent -- safe to re-run; already-downloaded assets are
    skipped (Requirement #5).
  * Atomic writes -- each download lands in a `<file>.part` file and
    is only moved into place once the transfer is verified complete
    (byte count matches the server's Content-Length). A dropped
    connection or Ctrl+C can therefore never leave a corrupt file
    sitting at the final path pretending to be a finished asset.
  * Total footprint is ~46 MB, comfortably inside the 150 MB
    RAM/storage budget for the edge device (see MODEL NOTES).

MODEL NOTES
-----------
STT: we deliberately use
`csukuangfj/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17`
rather than the more commonly-referenced `...-en-2023-06-26`
checkpoint. Both are official k2-fsa / sherpa-onnx releases, but the
06-26 model's INT8 encoder alone is ~180 MB -- that would blow the
whole 150 MB budget on the encoder alone. The 20M-parameter
checkpoint used here is exported specifically for low-power /
Cortex-A7-class CPUs (it comes from icefall's
`pruned-transducer-stateless7-streaming-small` recipe), and its full
INT8 encoder + decoder + joiner set totals well under 50 MB.

Sources (both permissively licensed, official upstream):
  VAD -- https://github.com/snakers4/silero-vad                (MIT)
  STT -- https://github.com/k2-fsa/sherpa-onnx                 (Apache-2.0)
         https://huggingface.co/csukuangfj/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17

Usage
-----
    python setup_assets.py            # fetch only what's missing
    python setup_assets.py --force    # re-download everything
=====================================================================
"""

import argparse
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# --------------------------------------------------------------------------- #
# 1. Configuration
# --------------------------------------------------------------------------- #

# Resolve every path relative to *this file*, not the shell's current
# working directory, so `python setup_assets.py` works no matter where
# it's invoked from.
SENDER_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = SENDER_ROOT / "assets"
VAD_DIR = ASSETS_DIR / "vad"
STT_DIR = ASSETS_DIR / "stt"

_HF_STT_REPO = (
    "https://huggingface.co/csukuangfj/"
    "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17/resolve/main"
)

# Each entry: (human label, source URL, destination path).
# The STT files are downloaded as their INT8-quantized originals and
# simply renamed at the destination (encoder-epoch-99-avg-1.int8.onnx
# -> encoder-epoch-99-avg-1.onnx) to match the exact filenames the
# sender engine expects.
ASSET_MANIFEST = [
    (
        "Silero VAD",
        "https://raw.githubusercontent.com/snakers4/silero-vad/master/"
        "src/silero_vad/data/silero_vad.onnx",
        VAD_DIR / "silero_vad.onnx",
    ),
    (
        "Zipformer STT - Encoder (INT8)",
        f"{_HF_STT_REPO}/encoder-epoch-99-avg-1.int8.onnx",
        STT_DIR / "encoder-epoch-99-avg-1.onnx",
    ),
    (
        "Zipformer STT - Decoder (INT8)",
        f"{_HF_STT_REPO}/decoder-epoch-99-avg-1.int8.onnx",
        STT_DIR / "decoder-epoch-99-avg-1.onnx",
    ),
    (
        "Zipformer STT - Joiner (INT8)",
        f"{_HF_STT_REPO}/joiner-epoch-99-avg-1.int8.onnx",
        STT_DIR / "joiner-epoch-99-avg-1.onnx",
    ),
    (
        "Zipformer STT - Tokens (vocab)",
        f"{_HF_STT_REPO}/tokens.txt",
        STT_DIR / "tokens.txt",
    ),
]

REQUEST_HEADERS = {"User-Agent": "iTantra-Neural-Transceiver-SetupAssets/1.0"}
CHUNK_SIZE = 256 * 1024   # 256 KB per read: smooth progress bar, low memory use
MAX_ATTEMPTS = 3          # retries per file before giving up
MIN_VALID_BYTES = 1024    # anything smaller can't be a real model/vocab file


# --------------------------------------------------------------------------- #
# 2. Small display utilities
# --------------------------------------------------------------------------- #

def human_size(num_bytes: float) -> str:
    """Render a byte count as a friendly string, e.g. '42.8 MB'."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"  # unreachable, keeps linters happy


def render_progress(label: str, downloaded: int, total: int, start_time: float, bar_width: int = 30) -> None:
    """Draw a single-line, in-place progress bar (Requirement #3)."""
    elapsed = max(time.time() - start_time, 1e-6)
    speed = downloaded / elapsed  # bytes/sec

    if total > 0:
        fraction = min(downloaded / total, 1.0)
        filled = int(bar_width * fraction)
        bar = "#" * filled + "-" * (bar_width - filled)
        line = (
            f"\r  [{bar}] {fraction * 100:5.1f}%  "
            f"{human_size(downloaded):>9} / {human_size(total):<9} "
            f"@ {human_size(speed)}/s  {label}"
        )
    else:
        # Some servers omit Content-Length; fall back to a raw byte counter
        # instead of a percentage bar so we degrade gracefully.
        line = f"\r  [downloading] {human_size(downloaded):>9}  @ {human_size(speed)}/s  {label}"

    # Pad so a shorter line fully overwrites a longer previous one.
    sys.stdout.write(line.ljust(100))
    sys.stdout.flush()


# --------------------------------------------------------------------------- #
# 3. Core download logic
# --------------------------------------------------------------------------- #

def is_already_present(dest: Path) -> bool:
    """Idempotency check (Requirement #5). A file counts as 'already
    downloaded' only if it exists AND clears a trivial size sanity
    threshold -- guards against trusting a half-written file left
    behind by an earlier interrupted run."""
    return dest.exists() and dest.stat().st_size >= MIN_VALID_BYTES


def download_one(label: str, url: str, dest: Path) -> None:
    """Stream `url` into `dest` with a live progress bar, automatic
    retries, and an atomic rename so `dest` never briefly contains a
    partial file."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest.with_name(dest.name + ".part")

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            request = urllib.request.Request(url, headers=REQUEST_HEADERS)
            with urllib.request.urlopen(request, timeout=30) as response:
                total = int(response.getheader("Content-Length") or 0)
                downloaded = 0
                start_time = time.time()

                with open(tmp_path, "wb") as fh:
                    while True:
                        chunk = response.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        fh.write(chunk)
                        downloaded += len(chunk)
                        render_progress(label, downloaded, total, start_time)

            # If the server promised a size up front, hold the download to
            # that promise. A mismatch means the connection dropped mid-
            # transfer and we got a silently truncated file.
            if total and downloaded != total:
                raise IOError(f"expected {total} bytes but received {downloaded}")

            os.replace(tmp_path, dest)  # atomic on POSIX and on Windows
            print()  # advance past the progress line
            return

        except (urllib.error.URLError, TimeoutError, IOError, OSError) as exc:
            last_error = exc
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
            print(f"\n  Attempt {attempt}/{MAX_ATTEMPTS} failed for {label}: {exc}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(2 * attempt)  # brief backoff before retrying

    raise RuntimeError(f"giving up after {MAX_ATTEMPTS} attempts ({last_error})")


# --------------------------------------------------------------------------- #
# 4. Optional, non-blocking runtime sanity check
# --------------------------------------------------------------------------- #

def check_runtime_environment() -> None:
    """main_sender.py needs `onnxruntime` at runtime. We deliberately do
    NOT install it here (this script must stay dependency-free per
    Requirement #2) -- we just give a friendly heads-up if it's missing
    so 'assets downloaded fine but the sender won't start' isn't a
    surprise."""
    try:
        import onnxruntime  # noqa: F401 (import is the check)
        print(f"[OK]   onnxruntime detected (v{onnxruntime.__version__}) -- ready to run main_sender.py")
    except ImportError:
        print(
            "[NOTE] 'onnxruntime' isn't installed in this Python environment yet.\n"
            "       main_sender.py needs it at runtime:  pip install onnxruntime\n"
            "       (left out of this script on purpose -- see Requirement #2)"
        )


# --------------------------------------------------------------------------- #
# 5. Orchestration
# --------------------------------------------------------------------------- #

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download the VAD + STT ONNX assets for the iTantra Neural Transceiver sender."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download every asset even if a local copy already exists.",
    )
    args = parser.parse_args()

    print("=" * 72)
    print(" iTantra Neural Transceiver -- Sender Asset Setup")
    print("=" * 72)
    print(f"Target directory: {ASSETS_DIR}\n")

    VAD_DIR.mkdir(parents=True, exist_ok=True)   # Requirement #4
    STT_DIR.mkdir(parents=True, exist_ok=True)   # Requirement #4

    failures = []
    for label, url, dest in ASSET_MANIFEST:
        rel = dest.relative_to(SENDER_ROOT)

        if not args.force and is_already_present(dest):
            print(f"[SKIP] {label:<32} already present ({human_size(dest.stat().st_size)})  -> {rel}")
            continue

        print(f"[GET ] {label:<32} -> {rel}")
        try:
            download_one(label, url, dest)
        except RuntimeError as exc:
            print(f"[FAIL] {label}: {exc}")
            failures.append(label)

    print("\n" + "=" * 72)
    if failures:
        print(f" Setup FAILED for {len(failures)} asset(s): {', '.join(failures)}")
        print(" Check your network connection and re-run this script -- it only")
        print(" re-downloads what's still missing, so it's safe to retry.")
        print("=" * 72)
        return 1

    total_size = sum(f.stat().st_size for f in ASSETS_DIR.rglob("*") if f.is_file())
    print(" All assets ready:")
    for _, _, dest in ASSET_MANIFEST:
        print(f"   {dest.relative_to(SENDER_ROOT)}")
    print(f"\n Total on-disk footprint: {human_size(total_size)}  (budget: 150 MB)")
    print()
    check_runtime_environment()
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())