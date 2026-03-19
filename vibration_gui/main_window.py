"""
Main application window for the Vibration Analysis Suite.
"""
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTextEdit, QSplitter, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor

from .styles import (
    DARK_QSS, LIGHT_QSS, LOG_COLORS,
    header_bar_style, console_wrap_style, console_header_style,
    theme_toggle_style,
)
from . import plot_utils
from .crop_tab import CropTab
from .fft_tab import FFTTab
from .spectrogram_tab import SpectrogramTab


class MainWindow(QMainWindow):

    VERSION = "1.0"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Vibration Analysis Suite  v{self.VERSION}")
        self.setMinimumSize(1100, 720)
        self.resize(1440, 900)
        self._dark = False         # start in light mode
        self._build_ui()
        self._apply_theme(dark=False)

    # ─────────────────────────────────────────────────────────────────────────
    # Build UI
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header bar ──────────────────────────────────────────────────────
        self._header_bar = QWidget()
        self._header_bar.setFixedHeight(36)
        header_layout = QHBoxLayout(self._header_bar)
        header_layout.setContentsMargins(8, 0, 8, 0)
        header_layout.setSpacing(0)

        self._header_title = QLabel(
            f"  ◈  Vibration Analysis Suite  —  v{self.VERSION}"
            f"  |  AccX / AccY / AccZ  |  FFT · Spectrogram · Crop"
        )
        self._header_title.setStyleSheet(
            "font-size:12px; font-weight:bold; background:transparent;"
        )

        self._header_credit = QLabel("developed by  Akshat_EA")
        self._header_credit.setStyleSheet(
            "font-size:10px; font-weight:normal; background:transparent;"
            "letter-spacing:0.5px;"
        )

        self._btn_theme = QPushButton()
        self._btn_theme.setFixedSize(110, 26)
        self._btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_theme.clicked.connect(self._toggle_theme)

        header_layout.addWidget(self._header_title, stretch=1)
        header_layout.addWidget(self._header_credit, stretch=0)
        header_layout.setSpacing(12)
        header_layout.addWidget(self._btn_theme, stretch=0)

        layout.addWidget(self._header_bar)

        # ── Vertical splitter: tabs (top) + console (bottom) ────────────────
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.fft_tab  = FFTTab(self._log)
        self.crop_tab = CropTab(self._log, add_to_fft_fn=self.fft_tab.load_file)
        self.spec_tab = SpectrogramTab(self._log)

        self.tabs.addTab(self.crop_tab, "  ✂  Raw Crop  ")
        self.tabs.addTab(self.fft_tab,  "  ∿  FFT Analyzer  ")
        self.tabs.addTab(self.spec_tab, "  ◈  Spectrogram  ")

        splitter.addWidget(self.tabs)

        # Console
        self._console_wrap = QWidget()
        cwl = QVBoxLayout(self._console_wrap)
        cwl.setContentsMargins(0, 0, 0, 0)
        cwl.setSpacing(0)

        self._console_header = QLabel("  Console Output")
        self._console_header.setFixedHeight(22)
        cwl.addWidget(self._console_header)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas" if sys.platform == "win32" else "Menlo", 10))
        cwl.addWidget(self.console)

        splitter.addWidget(self._console_wrap)
        splitter.setSizes([750, 130])
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)

        self._log("Vibration Analysis Suite ready.")
        self._log("  ✂  Raw Crop      — load, inspect, crop and export .bin files")
        self._log("  ∿  FFT Analyzer  — overlay FFT & time-domain for multiple files")
        self._log("  ◈  Spectrogram   — white-hot spectrogram")

    # ─────────────────────────────────────────────────────────────────────────
    # Theme
    # ─────────────────────────────────────────────────────────────────────────

    def _toggle_theme(self):
        self._apply_theme(dark=not self._dark)

    def _apply_theme(self, dark: bool):
        self._dark = dark

        # Update matplotlib colour palette first (tabs read from plot_utils globals)
        plot_utils.apply_theme(dark)

        # Global QSS
        self.setStyleSheet(DARK_QSS if dark else LIGHT_QSS)

        # Header bar background + title colour
        self._header_bar.setStyleSheet(
            f"background-color:{'#11111b' if dark else '#e8eaf6'};"
            f"border-bottom:1px solid {'#313244' if dark else '#c5cae9'};"
        )
        self._header_title.setStyleSheet(
            f"font-size:12px; font-weight:bold; background:transparent;"
            f"color:{'#89b4fa' if dark else '#1e66f5'};"
        )

        # Credit label
        self._header_credit.setStyleSheet(
            f"font-size:10px; font-weight:normal; background:transparent;"
            f"letter-spacing:0.5px;"
            f"color:{'#45475a' if dark else '#9ca0b0'};"
        )

        # Toggle button
        self._btn_theme.setText("☀  Light Mode" if dark else "🌙  Dark Mode")
        self._btn_theme.setStyleSheet(theme_toggle_style(dark))

        # Console wrapper + header
        self._console_wrap.setStyleSheet(console_wrap_style(dark))
        self._console_header.setStyleSheet(
            console_header_style(dark) + " font-size:10px; font-weight:bold; padding-left:6px;"
        )

        # Redraw all tab plots with new palette
        self.crop_tab.redraw_theme()
        self.fft_tab.redraw_theme()
        self.spec_tab.redraw_theme()

    # ─────────────────────────────────────────────────────────────────────────
    # Logging
    # ─────────────────────────────────────────────────────────────────────────

    def _log(self, message: str):
        """Append a colour-coded line to the console."""
        colors = LOG_COLORS[self._dark]
        if message.startswith("[Crop]"):
            color = colors["[Crop]"]
        elif message.startswith("[FFT]"):
            color = colors["[FFT]"]
        elif message.startswith("[Spec]"):
            color = colors["[Spec]"]
        else:
            color = colors["default"]

        self.console.append(
            f'<span style="color:{color}; font-family:Consolas,Menlo,Monaco,\'Courier New\',monospace;">» {message}</span>'
        )
        self.console.moveCursor(QTextCursor.MoveOperation.End)
