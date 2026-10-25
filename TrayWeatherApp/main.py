"""Application entry point, shared by module and executable launches."""
import argparse
from TrayWeatherApp._version import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(description="TrayWeatherApp system tray weather monitor")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args(argv)
    from TrayWeatherApp.app import TrayWeatherApp
    app = TrayWeatherApp()
    app.run()


if __name__ == "__main__":
    main()
