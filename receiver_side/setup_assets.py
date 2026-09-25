"""
Receiver Side Asset Setup Script
Downloads lightweight, pre-trained Sherpa-ONNX / MMS-VITS TTS models and vocabulary tokens.
"""

import os
import tarfile
from pathlib import Path
import requests
from tqdm import tqdm

# High-efficiency, offline English TTS model (Sherpa-ONNX VITS)
TTS_MODEL_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-en_US-amy-low.tar.bz2"


def download_file(url: str, dest_path: Path) -> None:
    """Downloads a file with progress tracking."""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    total_size = int(response.headers.get('content-length', 0))

    with open(dest_path, 'wb') as file, tqdm(
        desc=dest_path.name,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            bar.update(size)


def setup_tts_assets() -> None:
    assets_dir = Path(__file__).parent / "assets" / "tts"
    assets_dir.mkdir(parents=True, exist_ok=True)

    print("==========================================")
    print("      ITANTRA RECEIVER ASSETS SETUP       ")
    print("==========================================\n")

    model_file = assets_dir / "model.onnx"
    tokens_file = assets_dir / "tokens.txt"

    if model_file.exists() and tokens_file.exists():
        print("✅ All TTS ONNX assets are already downloaded and present in 'receiver_side/assets/tts/'.")
        return

    archive_path = assets_dir / "vits_tts_model.tar.bz2"
    print(f"📥 Downloading lightweight TTS neural weights from Sherpa-ONNX releases...")
    
    try:
        download_file(TTS_MODEL_URL, archive_path)
        print("📦 Extracting archive...")
        
        with tarfile.open(archive_path, "r:bz2") as tar:
            tar.extractall(path=assets_dir)

        # Reorganize extracted model files directly into assets/tts/
        extracted_folder = assets_dir / "vits-piper-en_US-amy-low"
        if extracted_folder.exists():
            for file in extracted_folder.iterdir():
                file.rename(assets_dir / file.name)
            extracted_folder.rmdir()

        # Clean up archive
        if archive_path.exists():
            archive_path.unlink()

        print("\n🎉 TTS Model setup complete! Model ready at 'receiver_side/assets/tts/model.onnx'.")

    except Exception as e:
        print(f"\n❌ Error downloading TTS assets: {e}")
        print("Fallback: The TTS engine will run in synthetic tone fallback mode until assets are placed.")


if __name__ == "__main__":
    setup_tts_assets()