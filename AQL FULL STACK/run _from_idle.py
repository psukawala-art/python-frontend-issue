import os
import sys
import subprocess
import importlib.util
from pathlib import Path


def launch_airscope():
    # Find the folder containing this launcher.
    project_folder = Path(__file__).resolve().parent

    # Main Streamlit dashboard.
    main_file = project_folder / "main.py"

    # Check that the dashboard exists.
    if not main_file.exists():
        print("ERROR: main.py was not found.")
        print("Keep run_from_idle.py and main.py in the same folder.")
        return

    # Check that Streamlit is installed in this Python environment.
    if importlib.util.find_spec("streamlit") is None:
        print("Streamlit is not installed in this Python environment.")
        print("Open the macOS Terminal and run:")
        print("python3 -m pip install streamlit pandas plotly")
        return

    print("=" * 45)
    print("Starting AirScope AQI Dashboard...")
    print("Please wait while Streamlit starts.")
    print("=" * 45)

    # Launch the dashboard using Streamlit's proper runner.
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(main_file),
        "--server.headless",
        "true",
    ]

    try:
        subprocess.Popen(
            command,
            cwd=str(project_folder),
        )

        print("AirScope is starting.")
        print("Open this address in your browser:")
        print("http://localhost:8501")

    except Exception as error:
        print("Unable to start AirScope.")
        print(type(error).__name__ + ":", error)


if __name__ == "__main__":
    launch_airscope()
