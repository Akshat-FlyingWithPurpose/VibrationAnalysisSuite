"""
Vibration Analysis Suite — Entry Point

Equivalent Python pipeline for:
  RawCrop.m           → Raw Crop tab
  VibeDriver.m        → FFT Analyzer tab
  Spectrogram_SFFT.m  → Spectrogram / SFFT tab

Usage:
    python main.py
"""
import sys

# Set matplotlib backend BEFORE any matplotlib or GUI imports
import matplotlib
matplotlib.use("QtAgg")

from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from vibration_gui.main_window import MainWindow

_PASSWORD     = "aezakmi"
_MAX_ATTEMPTS = 3
_ALLOWED      = _MAX_ATTEMPTS   # total wrong attempts before lockout


class PasswordDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vibration Analysis Suite")
        self.setFixedSize(340, 200)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.CustomizeWindowHint
        )
        self._attempts = 0
        self._accepted = False
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog   { background:#eff1f5; }
            QLabel    { color:#4c4f69; font-size:11px; }
            QLabel#title { font-size:14px; font-weight:bold; color:#1e66f5; }
            QLabel#error { color:#d20f39; font-size:10px; }
            QLineEdit {
                background:#ffffff; color:#4c4f69;
                border:1px solid #bcc0cc; border-radius:5px;
                padding:6px 10px; font-size:12px;
            }
            QLineEdit:focus { border-color:#1e66f5; }
            QPushButton {
                background:#1e66f5; color:#eff1f5;
                border:none; border-radius:5px;
                padding:7px 20px; font-size:11px; font-weight:bold;
            }
            QPushButton:hover    { background:#3576f5; }
            QPushButton:pressed  { background:#0a50e0; }
            QPushButton:disabled { background:#bcc0cc; color:#eff1f5; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(12)

        title = QLabel("◈  Vibration Analysis Suite")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addWidget(QLabel("Enter password to continue:"))

        self._field = QLineEdit()
        self._field.setEchoMode(QLineEdit.EchoMode.Password)
        self._field.setPlaceholderText("Password")
        self._field.returnPressed.connect(self._check)
        layout.addWidget(self._field)

        self._lbl_error = QLabel("")
        self._lbl_error.setObjectName("error")
        self._lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl_error)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_unlock = QPushButton("Unlock")
        self._btn_unlock.setFixedWidth(100)
        self._btn_unlock.setAutoDefault(False)   # prevent Enter key double-firing via button
        self._btn_unlock.setDefault(False)
        self._btn_unlock.clicked.connect(self._check)
        btn = self._btn_unlock
        btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _check(self):
        if self._field.text() == _PASSWORD:
            self._accepted = True
            self.accept()
            return

        self._attempts += 1
        self._field.clear()

        if self._attempts >= _MAX_ATTEMPTS:
            self._lbl_error.setText(
                "Too many wrong attempts.\n"
                "Contact Akshat_EA for further information.\n"
                "Closing…"
            )
            self._field.setEnabled(False)
            self._btn_unlock.setEnabled(False)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(10000, self.reject)
        else:
            remaining = _MAX_ATTEMPTS - self._attempts
            self._lbl_error.setText(
                f"Incorrect password. {remaining} attempt{'s' if remaining > 1 else ''} left."
            )


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setApplicationName("Vibration Analysis Suite")

    dlg = PasswordDialog()
    dlg.exec()

    if not dlg._accepted:
        sys.exit(0)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
