#!/usr/bin/env python3
"""
Quick launcher for Smart Research Assistant Frontend

This script provides an easy way to start the Streamlit frontend
with proper environment setup and error handling.
"""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import streamlit

        import mcp_tx

        print("✅ All dependencies available")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: uv sync")
        return False


def start_frontend():
    """Start the Streamlit frontend."""
    if not check_dependencies():
        return

    # Get the directory of this script
    script_dir = Path(__file__).parent
    frontend_path = script_dir / "research_frontend.py"

    if not frontend_path.exists():
        print("❌ Frontend file not found!")
        return

    print("🚀 Starting Smart Research Assistant Frontend...")
    print("📍 Frontend will be available at: http://localhost:8501")
    print("⏳ Opening browser in 3 seconds...")

    # Start Streamlit
    try:
        # Schedule browser opening
        import threading

        def open_browser():
            time.sleep(3)
            webbrowser.open("http://localhost:8501")

        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()

        # Start Streamlit with browser auto-open disabled
        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(frontend_path),
            "--server.port",
            "8501",
            "--server.address",
            "localhost",
            "--browser.gatherUsageStats",
            "false",
            "--server.headless",
            "true",
        ]

        subprocess.run(cmd)

    except KeyboardInterrupt:
        print("\n👋 Frontend stopped by user")
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")


if __name__ == "__main__":
    start_frontend()
