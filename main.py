from pathlib import Path
import subprocess
import sys


def main():
    app_path = Path(__file__).with_name("app.py")
    command = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())