#!/usr/bin/env python3
"""Check system compatibility for Gemini STT."""

import sys
import subprocess
import shutil


def check_python_version():
    """Check Python version compatibility."""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version < (3, 8):
        print("❌ ERROR: Python 3.8 or higher is required")
        return False
    elif version >= (3, 13):
        print("⚠️  WARNING: Python 3.13+ detected")
        print("   The audioop module was removed in Python 3.13")
        print("   Audio processing will work but with limited functionality")
        print("   For best compatibility, consider using Python 3.10-3.12")
        return True
    else:
        print("✅ Python version is fully compatible")
        return True


def check_ffmpeg():
    """Check if FFmpeg is installed."""
    if shutil.which("ffmpeg"):
        try:
            result = subprocess.run(["ffmpeg", "-version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ FFmpeg is installed")
                # Extract version
                lines = result.stdout.split('\n')
                if lines:
                    print(f"   {lines[0]}")
                return True
        except:
            pass
    
    print("❌ FFmpeg not found")
    print("   FFmpeg is required for video/audio processing")
    print("   Download from: https://ffmpeg.org/download.html")
    return False


def check_pip_packages():
    """Check if required packages can be installed."""
    print("\nChecking package availability...")
    
    critical_packages = [
        "google-api-python-client",
        "google-generativeai",
        "pydub",
        "tqdm",
        "requests",
        "python-dotenv"
    ]
    
    for package in critical_packages:
        try:
            subprocess.run([sys.executable, "-m", "pip", "show", package],
                         capture_output=True, check=True)
            print(f"✅ {package} is installed")
        except subprocess.CalledProcessError:
            print(f"ℹ️  {package} will be installed")


def main():
    print("="*60)
    print("Gemini STT Compatibility Check")
    print("="*60)
    print()
    
    # Check Python version
    python_ok = check_python_version()
    print()
    
    # Check FFmpeg
    ffmpeg_ok = check_ffmpeg()
    print()
    
    # Check packages
    check_pip_packages()
    
    print()
    print("="*60)
    
    if python_ok and ffmpeg_ok:
        print("✅ System is ready for Gemini STT")
    else:
        print("⚠️  Some components need attention")
        
    if sys.version_info >= (3, 13):
        print()
        print("Recommendation for Python 3.13+ users:")
        print("1. The pipeline will work but with warnings")
        print("2. For production use, consider Python 3.12")
        print("3. Install Python 3.12 alongside 3.13:")
        print("   - Windows: Download from python.org")
        print("   - Use py -3.12 instead of python")
    
    print("="*60)


if __name__ == "__main__":
    main()