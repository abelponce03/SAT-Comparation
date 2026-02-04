"""
Quick start script for SAT Benchmark Suite
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("=" * 60)
    print("🔬 SAT Benchmark Suite - Quick Start")
    print("=" * 60)
    print()
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    else:
        print(f"✅ Python {sys.version.split()[0]}")
    
    # Check if requirements are installed
    print("\n📦 Checking dependencies...")
    try:
        import streamlit
        import pandas
        import plotly
        print("✅ All dependencies installed")
    except ImportError as e:
        print(f"❌ Missing dependency: {e.name}")
        print("\n📥 Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Check directory structure
    print("\n📁 Checking directory structure...")
    required_dirs = [
        "app", "app/pages", "app/core", "app/analysis", "app/utils",
        "solvers", "benchmarks", "results", "config", "temp"
    ]
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"  ✅ {dir_path}/")
        else:
            print(f"  ❌ {dir_path}/ (missing)")
    
    # Start the application
    print("\n" + "=" * 60)
    print("🚀 Starting SAT Benchmark Suite...")
    print("=" * 60)
    print("\n📍 The application will open in your browser at:")
    print("   http://localhost:8503")
    print("\n⚠️  Press Ctrl+C to stop the server")
    print()
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "app/main.py",
            "--server.headless", "true"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down SAT Benchmark Suite...")
        print("   Thank you for using the application!")

if __name__ == "__main__":
    main()
