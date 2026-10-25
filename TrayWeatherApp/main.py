"""Application entry point, shared by module and executable launches."""
import argparse
import os
import sys
from TrayWeatherApp._version import __version__


def configure_platform():
    """Prefer X11/XWayland window positioning on Linux before Qt is imported."""
    if sys.platform.startswith("linux") and os.environ.get("DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")


def main(argv=None):
    parser = argparse.ArgumentParser(description="TrayWeatherApp system tray weather monitor")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args(argv)
    configure_platform()
    from TrayWeatherApp.app import TrayWeatherApp
    app = TrayWeatherApp()
    app.run()


if __name__ == "__main__":
    main()
