"""
Cross-Platform C++ Native Module Build Script
Compiles c_src/packet_parser.cpp into a shared library (.so / .dll).
"""

import os
import subprocess
import sys
from pathlib import Path


def build_cpp_extension():
    root_dir = Path(__file__).parent
    src_file = root_dir / "c_src" / "packet_parser.cpp"
    
    if sys.platform.startswith("win"):
        output_lib = root_dir / "receiver_side" / "core" / "libpacket_parser.dll"
        cmd = ["g++", "-O3", "-shared", "-o", str(output_lib), str(src_file)]
    else:
        output_lib = root_dir / "receiver_side" / "core" / "libpacket_parser.so"
        cmd = ["g++", "-O3", "-fPIC", "-shared", "-o", str(output_lib), str(src_file)]

    print("==========================================")
    print("      COMPILING NATIVE C++ MODULE         ")
    print("==========================================\n")
    print(f"🔨 Compiling {src_file.name} -> {output_lib.name}...")

    try:
        subprocess.check_call(cmd)
        print(f"✅ Successfully compiled native C++ library: {output_lib}")
    except FileNotFoundError:
        print("⚠️ 'g++' compiler not found in PATH. Build skipped.")
        print("   (The Python depacketizer will automatically fall back to pure-Python parsing).")
    except Exception as e:
        print(f"❌ Compilation failed: {e}")


if __name__ == "__main__":
    build_cpp_extension()