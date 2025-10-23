
from .app import TrayWeatherApp

if __name__ == '__main__':
    app = TrayWeatherApp()
    app.theme.apply_to_app(app.app)
    app.app.exec()
