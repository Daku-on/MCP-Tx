"""
Launcher for the Multi-Agent Research Assistant Frontend
"""

import subprocess
from pathlib import Path


def start_frontend():
    """Starts the Streamlit frontend for the multi-agent demo."""
    script_dir = Path(__file__).parent
    frontend_path = script_dir / "multi_agent_frontend.py"

    if not frontend_path.exists():
        print(f"❌ Frontend file not found at: {frontend_path}")
        return

    print("🚀 Starting Multi-Agent Research Assistant Frontend...")
    print("📍 Your browser will open at: http://localhost:8501")

    cmd = [
        "streamlit",
        "run",
        str(frontend_path),
        "--server.port",
        "8501",
        "--server.address",
        "localhost",
    ]

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 Frontend stopped by user.")
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")


if __name__ == "__main__":
    start_frontend()
