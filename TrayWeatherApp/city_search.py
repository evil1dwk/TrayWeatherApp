"""Nonblocking location search with explicit selection of a geocoding result."""
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QLabel,
)
from TrayWeatherApp.workers import search_locations, location_label


class SearchSignals(QObject):
    completed = pyqtSignal(object, str)


class SearchTask(QRunnable):
    def __init__(self, query):
        super().__init__()
        self.query = query
        self.signals = SearchSignals()

    def run(self):
        try:
            self.signals.completed.emit(search_locations(self.query), "")
        except Exception as exc:
            self.signals.completed.emit([], str(exc))


class CitySearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add City")
        self.resize(550, 360)
        self.locations = []
        self.selected_location = None
        self.query = QLineEdit()
        self.query.setPlaceholderText("City or postal code (e.g. Springfield)")
        self.search_button = QPushButton("Search")
        search_row = QHBoxLayout()
        search_row.addWidget(self.query)
        search_row.addWidget(self.search_button)
        self.results = QListWidget()
        self.status = QLabel("Search, then select a city with its state/province and country.")
        self.status.setWordWrap(True)
        self.add_button = QPushButton("Add City")
        self.add_button.setEnabled(False)
        cancel = QPushButton("Cancel")
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(self.add_button)
        layout = QVBoxLayout(self)
        layout.addLayout(search_row)
        layout.addWidget(self.results)
        layout.addWidget(self.status)
        layout.addLayout(buttons)
        self.search_button.clicked.connect(self.search)
        self.query.returnPressed.connect(self.search)
        self.results.currentRowChanged.connect(lambda row: self.add_button.setEnabled(
            0 <= row < len(self.locations)))
        self.results.itemDoubleClicked.connect(lambda _: self.accept())
        self.add_button.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)

    def search(self):
        if not self.search_button.isEnabled():
            return
        query = self.query.text().strip()
        if len(query) < 2:
            self.status.setText("Enter at least two characters.")
            return
        self.locations = []
        self.results.clear()
        self.add_button.setEnabled(False)
        self.search_button.setEnabled(False)
        self.status.setText("Searching…")
        self.task = SearchTask(query)
        self.task.signals.completed.connect(self.show_results)
        QThreadPool.globalInstance().start(self.task)

    @pyqtSlot(object, str)
    def show_results(self, locations, error):
        self.search_button.setEnabled(True)
        self.locations = locations
        self.results.addItems([f"{location_label(loc)}  ({loc['latitude']:.3f}, {loc['longitude']:.3f})"
                               for loc in locations])
        self.status.setText(f"Search failed: {error}" if error else
                            "Select the correct location, then Add City." if locations else
                            "No matches found. Try a nearby city or a postal code.")

    def accept(self):
        row = self.results.currentRow()
        if 0 <= row < len(self.locations):
            self.selected_location = dict(self.locations[row])
            super().accept()
