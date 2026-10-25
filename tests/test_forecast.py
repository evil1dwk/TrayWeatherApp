import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PyQt6.QtCore import QEvent, QCoreApplication
from PyQt6.QtWidgets import QApplication
from TrayWeatherApp.forecast import parse_daily
from TrayWeatherApp.workers import WeatherWorker
from TrayWeatherApp.weather import WeatherWindow
from TrayWeatherApp.theme import ThemeManager
from TrayWeatherApp.weather_cache import WeatherCache


def daily():
    return {"time": [(date.today()+timedelta(days=i)).isoformat() for i in range(5)],
            "temperature_2m_max": [70,65,68,72,69],
            "temperature_2m_min": [46,48,45,49,47], "weather_code": [0,61,2,0,3],
            "precipitation_probability_max": [10,80,20,5,30]}


class ForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.owner = SimpleNamespace(config={}, theme=ThemeManager(), cities=["city"], locations={},
                                     units="imperial", tray=None, save_config=Mock(), jobs={})
        self.window = WeatherWindow(self.owner)
        self.window.add_city_tab("city")
        self.info = {"city":"Chase City", "temp":68.7, "units":"imperial",
                     "updated_at":datetime.now(timezone.utc).isoformat(),
                     "forecast":parse_daily(daily(), WeatherWorker("city","imperial").map_weather_code)}

    def tearDown(self):
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)

    def test_request_fetches_current_and_forecast_together(self):
        response = Mock(status_code=200)
        response.json.return_value = {"current":{"temperature_2m":68.7}, "daily":daily()}
        worker = WeatherWorker("city","imperial", {"name":"Chase City","latitude":37,"longitude":-78})
        results=[]
        worker.finished.connect(lambda city,info:results.append(info))
        with patch("TrayWeatherApp.workers.requests.get",return_value=response) as get:
            worker.run()
        get.assert_called_once()
        self.assertEqual(get.call_args.kwargs["params"]["forecast_days"],5)
        self.assertIn("precipitation_probability_max",get.call_args.kwargs["params"]["daily"])
        self.assertEqual(len(results[0]["forecast"]),5)
        self.assertEqual(results[0]["forecast"][1]["precipitation_probability"],80)
        self.assertEqual(results[0]["forecast"][1]["description"],"Light rain")

    def test_missing_and_partial_arrays_are_safe(self):
        worker=WeatherWorker("city","metric")
        self.assertEqual(parse_daily({},worker.map_weather_code),[])
        values=daily()
        values["temperature_2m_min"]=[]
        values["precipitation_probability_max"]=[None,999]
        values["time"][0]="not-a-date"
        parsed=parse_daily(values,worker.map_weather_code)
        self.assertEqual(len(parsed),4)
        self.assertIsNone(parsed[0]["low"])
        self.assertIsNone(parsed[0]["precipitation_probability"])

    def test_five_days_in_both_views_without_resizing_or_request(self):
        self.window.update_city_tab("city",self.info)
        self.window.show()
        for mode,count,size in [("normal",5,(760,500)),("compact",5,(440,240))]:
            self.owner.config["view_mode"]=mode
            self.window.apply_view_mode()
            with patch("TrayWeatherApp.workers.requests.get") as get:
                self.window.select_forecast(True)
                self.qt.processEvents()
                get.assert_not_called()
            card=self.window.city_tabs["city"]["card"]
            panel=card.forecast_panel
            self.assertFalse(panel.isHidden())
            self.assertEqual(sum(not w.isHidden() for w,labels in panel.columns),count)
            self.assertEqual((self.window.width(),self.window.height()),size)
            self.assertGreaterEqual(panel.height(),panel.minimumSizeHint().height())
            self.assertGreaterEqual(panel.width(),panel.minimumSizeHint().width())
            for widget, labels in panel.columns:
                for label in labels:
                    self.assertGreater(label.font().pixelSize(), 0)
                    if not label.isHidden():
                        from PyQt6.QtGui import QFontMetricsF
                        self.assertLessEqual(QFontMetricsF(label.font()).horizontalAdvance(label.text()),
                                             label.contentsRect().width())
            self.assertGreater(panel.city.font().pixelSize(), 0)
            self.assertIn("80%",panel.columns[1][0].toolTip())
            self.assertEqual(panel.columns[1][1][4].isHidden(),mode=="compact")
            self.window.select_forecast(False)
            self.assertTrue(panel.isHidden())
            self.assertEqual(self.window.tabs.currentWidget(),self.window.city_tabs["city"]["container"])

    def test_forecast_cache_round_trip_and_legacy_cache_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"weather.json"
            cache=WeatherCache(path);cache.put("city","imperial",self.info)
            info=WeatherCache(path).get("city","imperial")
            self.window.update_city_tab("city",info)
            self.window.select_forecast(True)
            self.assertEqual(len(self.window.city_tabs["city"]["card"].forecast_panel.info["forecast"]),5)
            info.pop("forecast")
            self.window.update_city_tab("city",info)
            self.assertFalse(self.window.city_tabs["city"]["card"].forecast_panel.message.isHidden())

    def test_selection_applies_to_new_tabs_and_uses_theme_colors(self):
        self.window.select_forecast(True)
        self.window.add_city_tab("other")
        self.assertTrue(self.window.city_tabs["other"]["card"].forecast_mode)
        self.window.update_city_tab("city",self.info)
        self.owner.theme.select_theme("Light")
        self.window.retheme()
        panel=self.window.city_tabs["city"]["card"].forecast_panel
        self.assertIn(self.owner.theme.value("high_color"),panel.columns[0][1][2].styleSheet())
        self.owner.save_config.assert_called()

    def test_failed_refresh_keeps_cached_forecast_visible(self):
        from PyQt6.QtCore import QObject
        from TrayWeatherApp.app import TrayWeatherApp
        controller=TrayWeatherApp.__new__(TrayWeatherApp)
        QObject.__init__(controller)
        controller.window=self.window
        controller.units="imperial"
        controller.jobs={"city":{"token":"request","units":"imperial"}}
        self.window.update_city_tab("city",self.info)
        self.window.select_forecast(True)
        controller.weather_result("city",{"request_id":"request","units":"imperial","error":"offline"})
        panel=self.window.city_tabs["city"]["card"].forecast_panel
        self.assertEqual(len(panel.info["forecast"]),5)
        self.assertFalse(panel.isHidden())
        self.assertIn("offline",self.window.footer_status.toolTip())
