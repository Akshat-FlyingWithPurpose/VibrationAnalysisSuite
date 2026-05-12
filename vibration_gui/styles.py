"""
Dark & Light theme stylesheets for the Vibration Analysis Suite.
Dark  — Catppuccin Mocha palette.
Light — Catppuccin Latte palette.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Per-widget inline styles (header bar / console) — theme-aware helpers
# ─────────────────────────────────────────────────────────────────────────────

def header_bar_style(dark: bool) -> str:
    if dark:
        return (
            "background-color:#11111b; color:#89b4fa;"
            "font-size:12px; font-weight:bold; padding-left:8px;"
            "border-bottom:1px solid #313244;"
        )
    return (
        "background-color:#e8eaf6; color:#1e66f5;"
        "font-size:12px; font-weight:bold; padding-left:8px;"
        "border-bottom:1px solid #c5cae9;"
    )


def console_wrap_style(dark: bool) -> str:
    return "background-color:#11111b;" if dark else "background-color:#f5f5f5;"


def console_header_style(dark: bool) -> str:
    if dark:
        return (
            "background-color:#181825; color:#6c7086;"
            "font-size:10px; font-weight:bold; padding-left:6px;"
            "border-top:1px solid #313244; border-bottom:1px solid #313244;"
        )
    return (
        "background-color:#e8e8e8; color:#5c5f77;"
        "font-size:10px; font-weight:bold; padding-left:6px;"
        "border-top:1px solid #cccccc; border-bottom:1px solid #cccccc;"
    )


def theme_toggle_style(dark: bool) -> str:
    """Style for the ☀/🌙 toggle button inside the header bar."""
    if dark:
        return (
            "QPushButton{"
            "background:transparent; color:#cdd6f4;"
            "border:1px solid #45475a; border-radius:12px;"
            "padding:3px 12px; font-size:11px; font-weight:bold;}"
            "QPushButton:hover{background:#313244; border-color:#89b4fa; color:#89b4fa;}"
            "QPushButton:pressed{background:#45475a;}"
        )
    return (
        "QPushButton{"
        "background:transparent; color:#4c4f69;"
        "border:1px solid #bcc0cc; border-radius:12px;"
        "padding:3px 12px; font-size:11px; font-weight:bold;}"
        "QPushButton:hover{background:#dce0f4; border-color:#1e66f5; color:#1e66f5;}"
        "QPushButton:pressed{background:#bcc0cc;}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Log message colours per theme
# ─────────────────────────────────────────────────────────────────────────────

LOG_COLORS = {
    True: {          # dark
        "[Crop]":  "#89b4fa",
        "[FFT]":   "#a6e3a1",
        "[Spec]":  "#cba6f7",
        "default": "#a6adc8",
    },
    False: {         # light
        "[Crop]":  "#1565c0",
        "[FFT]":   "#2e7d32",
        "[Spec]":  "#6a1b9a",
        "default": "#424242",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Dark QSS
# ─────────────────────────────────────────────────────────────────────────────

DARK_QSS = """
/* ── Base ─────────────────────────────────────────────────────────────── */
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "SF Pro Text", "Helvetica Neue", "Arial", sans-serif;
    font-size: 11px;
}

/* ── Tabs ──────────────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #313244;
    background-color: #1e1e2e;
    border-radius: 0px;
}
QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    padding: 8px 22px;
    border: 1px solid #313244;
    border-bottom: none;
    font-size: 11px;
    font-weight: bold;
    min-width: 130px;
}
QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #89b4fa;
    border-top: 2px solid #89b4fa;
}
QTabBar::tab:hover:!selected {
    background-color: #2a2a3e;
    color: #cdd6f4;
}

/* ── Buttons ───────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 6px 14px;
    font-size: 11px;
    font-weight: bold;
}
QPushButton:hover  { background-color: #45475a; border-color: #89b4fa; }
QPushButton:pressed { background-color: #89b4fa; color: #1e1e2e; }
QPushButton:disabled { background-color: #181825; color: #45475a; border-color: #313244; }

/* ── GroupBox ──────────────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #313244;
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 8px;
    color: #89b4fa;
    font-weight: bold;
    font-size: 11px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

/* ── Labels ────────────────────────────────────────────────────────────── */
QLabel {
    color: #cdd6f4;
    font-size: 11px;
}

/* ── Spin boxes ────────────────────────────────────────────────────────── */
QDoubleSpinBox, QSpinBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 6px;
    font-size: 11px;
}
QDoubleSpinBox:focus, QSpinBox:focus { border-color: #89b4fa; }
QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {
    background-color: #45475a;
    border: none;
    width: 16px;
}
QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover,
QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {
    background-color: #89b4fa;
}

/* ── List widget ───────────────────────────────────────────────────────── */
QListWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 4px;
    font-size: 11px;
}
QListWidget::item { padding: 3px 6px; }
QListWidget::item:selected { background-color: #313244; color: #89b4fa; }
QListWidget::item:hover:!selected { background-color: #252535; }

/* ── Text console ──────────────────────────────────────────────────────── */
QTextEdit {
    background-color: #11111b;
    color: #a6e3a1;
    border: none;
    border-top: 1px solid #313244;
    font-family: "Consolas", "Menlo", "Monaco", "Courier New", monospace;
    font-size: 11px;
    padding: 4px;
}

/* ── Checkboxes ────────────────────────────────────────────────────────── */
QCheckBox { color: #cdd6f4; font-size: 11px; spacing: 6px; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #45475a;
    border-radius: 3px;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
    image: none;
}
QCheckBox::indicator:hover { border-color: #89b4fa; }

/* ── Splitter ──────────────────────────────────────────────────────────── */
QSplitter::handle { background-color: #313244; }
QSplitter::handle:horizontal { width: 2px; }
QSplitter::handle:vertical   { height: 2px; }

/* ── Scrollbars ────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #181825; width: 8px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #45475a; border-radius: 4px; min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #181825; height: 8px; margin: 0;
}
QScrollBar::handle:horizontal {
    background: #45475a; border-radius: 4px; min-width: 20px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Toolbar (matplotlib) ──────────────────────────────────────────────── */
QToolBar {
    background-color: #181825;
    border: none;
    border-bottom: 1px solid #313244;
    spacing: 2px;
    padding: 2px;
}
QToolButton {
    background-color: transparent;
    color: #cdd6f4;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 3px;
}
QToolButton:hover   { background-color: #313244; border-color: #45475a; }
QToolButton:pressed { background-color: #45475a; }
QToolButton:checked {
    background-color: #313244;
    border: 1px solid #89b4fa;
    color: #89b4fa;
}

/* ── Status / info labels ──────────────────────────────────────────────── */
QLabel#info  { color: #a6e3a1; font-size: 10px; }
QLabel#warn  { color: #f9e2af; font-size: 10px; }
QLabel#muted { color: #6c7086; font-size: 10px; }

/* ── Accent buttons ────────────────────────────────────────────────────── */
QPushButton#btn_load {
    background-color: #313244; color: #89b4fa;
    border: 1px solid #89b4fa; border-radius: 5px;
    padding: 6px 14px; font-weight: bold; font-size: 11px;
}
QPushButton#btn_load:hover   { background-color: #89b4fa; color: #1e1e2e; }
QPushButton#btn_load:pressed { background-color: #74c7ec; color: #1e1e2e; }

QPushButton#btn_action {
    background-color: #89b4fa; color: #1e1e2e;
    border: none; border-radius: 5px;
    padding: 8px; font-weight: bold; font-size: 12px;
}
QPushButton#btn_action:hover    { background-color: #74c7ec; }
QPushButton#btn_action:pressed  { background-color: #58c7d8; }
QPushButton#btn_action:disabled { background-color: #313244; color: #45475a; }

QPushButton#btn_save {
    background-color: #a6e3a1; color: #1e1e2e;
    border: none; border-radius: 5px;
    padding: 7px; font-weight: bold; font-size: 11px;
}
QPushButton#btn_save:hover    { background-color: #94e2d5; }
QPushButton#btn_save:pressed  { background-color: #79dac8; }
QPushButton#btn_save:disabled { background-color: #313244; color: #45475a; }

QPushButton#btn_spec {
    background-color: #cba6f7; color: #1e1e2e;
    border: none; border-radius: 5px;
    padding: 8px; font-weight: bold; font-size: 12px;
}
QPushButton#btn_spec:hover    { background-color: #b4befe; }
QPushButton#btn_spec:pressed  { background-color: #96a7f5; }
QPushButton#btn_spec:disabled { background-color: #313244; color: #45475a; }

/* ── File list scroll area ─────────────────────────────────────────────── */
QScrollArea#file_list {
    border: 1px solid #313244; border-radius: 4px; background: #11111b;
}

/* ── File row frames ───────────────────────────────────────────────────── */
QFrame#file_row { background: #1a1a2e; border-radius: 4px; }
QFrame#file_row:hover { background: #252540; }
"""

# Legacy inline style constants — kept for reference; no longer applied
BTN_LOAD_STYLE = """
QPushButton {
    background-color: #313244; color: #89b4fa;
    border: 1px solid #89b4fa; border-radius: 5px;
    padding: 6px 14px; font-weight: bold; font-size: 11px;
}
QPushButton:hover   { background-color: #89b4fa; color: #1e1e2e; }
QPushButton:pressed { background-color: #74c7ec; color: #1e1e2e; }
"""

BTN_ACTION_STYLE = """
QPushButton {
    background-color: #89b4fa; color: #1e1e2e;
    border: none; border-radius: 5px;
    padding: 8px; font-weight: bold; font-size: 12px;
}
QPushButton:hover   { background-color: #74c7ec; }
QPushButton:pressed { background-color: #58c7d8; }
QPushButton:disabled { background-color: #313244; color: #45475a; }
"""

BTN_SAVE_STYLE = """
QPushButton {
    background-color: #a6e3a1; color: #1e1e2e;
    border: none; border-radius: 5px;
    padding: 7px; font-weight: bold; font-size: 11px;
}
QPushButton:hover   { background-color: #94e2d5; }
QPushButton:pressed { background-color: #79dac8; }
QPushButton:disabled { background-color: #313244; color: #45475a; }
"""

BTN_SPEC_STYLE = """
QPushButton {
    background-color: #cba6f7; color: #1e1e2e;
    border: none; border-radius: 5px;
    padding: 8px; font-weight: bold; font-size: 12px;
}
QPushButton:hover   { background-color: #b4befe; }
QPushButton:pressed { background-color: #96a7f5; }
QPushButton:disabled { background-color: #313244; color: #45475a; }
"""


# ─────────────────────────────────────────────────────────────────────────────
# Light QSS  (Catppuccin Latte)
# ─────────────────────────────────────────────────────────────────────────────

LIGHT_QSS = """
/* ── Base ─────────────────────────────────────────────────────────────── */
QMainWindow, QWidget {
    background-color: #eff1f5;
    color: #4c4f69;
    font-family: "Segoe UI", "SF Pro Text", "Helvetica Neue", "Arial", sans-serif;
    font-size: 11px;
}

/* ── Tabs ──────────────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #ccd0da;
    background-color: #eff1f5;
    border-radius: 0px;
}
QTabBar::tab {
    background-color: #e6e9ef;
    color: #6c6f85;
    padding: 8px 22px;
    border: 1px solid #ccd0da;
    border-bottom: none;
    font-size: 11px;
    font-weight: bold;
    min-width: 130px;
}
QTabBar::tab:selected {
    background-color: #eff1f5;
    color: #1e66f5;
    border-top: 2px solid #1e66f5;
}
QTabBar::tab:hover:!selected {
    background-color: #dce0f4;
    color: #4c4f69;
}

/* ── Buttons ───────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #e6e9ef;
    color: #4c4f69;
    border: 1px solid #bcc0cc;
    border-radius: 5px;
    padding: 6px 14px;
    font-size: 11px;
    font-weight: bold;
}
QPushButton:hover  { background-color: #dce0f4; border-color: #1e66f5; }
QPushButton:pressed { background-color: #1e66f5; color: #eff1f5; }
QPushButton:disabled { background-color: #eff1f5; color: #bcc0cc; border-color: #ccd0da; }

/* ── GroupBox ──────────────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #ccd0da;
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 8px;
    color: #1e66f5;
    font-weight: bold;
    font-size: 11px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

/* ── Labels ────────────────────────────────────────────────────────────── */
QLabel {
    color: #4c4f69;
    font-size: 11px;
}

/* ── Spin boxes ────────────────────────────────────────────────────────── */
QDoubleSpinBox, QSpinBox {
    background-color: #ffffff;
    color: #4c4f69;
    border: 1px solid #bcc0cc;
    border-radius: 4px;
    padding: 4px 6px;
    font-size: 11px;
}
QDoubleSpinBox:focus, QSpinBox:focus { border-color: #1e66f5; }
QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {
    background-color: #e6e9ef;
    border: none;
    width: 16px;
}
QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover,
QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {
    background-color: #1e66f5;
}

/* ── List widget ───────────────────────────────────────────────────────── */
QListWidget {
    background-color: #ffffff;
    color: #4c4f69;
    border: 1px solid #ccd0da;
    border-radius: 4px;
    font-size: 11px;
}
QListWidget::item { padding: 3px 6px; }
QListWidget::item:selected { background-color: #dce0f4; color: #1e66f5; }
QListWidget::item:hover:!selected { background-color: #f0f2fa; }

/* ── Text console ──────────────────────────────────────────────────────── */
QTextEdit {
    background-color: #ffffff;
    color: #2e7d32;
    border: none;
    border-top: 1px solid #ccd0da;
    font-family: "Consolas", "Menlo", "Monaco", "Courier New", monospace;
    font-size: 11px;
    padding: 4px;
}

/* ── Checkboxes ────────────────────────────────────────────────────────── */
QCheckBox { color: #4c4f69; font-size: 11px; spacing: 6px; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #bcc0cc;
    border-radius: 3px;
    background-color: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #1e66f5;
    border-color: #1e66f5;
    image: none;
}
QCheckBox::indicator:hover { border-color: #1e66f5; }

/* ── Splitter ──────────────────────────────────────────────────────────── */
QSplitter::handle { background-color: #ccd0da; }
QSplitter::handle:horizontal { width: 2px; }
QSplitter::handle:vertical   { height: 2px; }

/* ── Scrollbars ────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #e6e9ef; width: 8px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #bcc0cc; border-radius: 4px; min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #e6e9ef; height: 8px; margin: 0;
}
QScrollBar::handle:horizontal {
    background: #bcc0cc; border-radius: 4px; min-width: 20px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Toolbar (matplotlib) ──────────────────────────────────────────────── */
QToolBar {
    background-color: #e6e9ef;
    border: none;
    border-bottom: 1px solid #ccd0da;
    spacing: 2px;
    padding: 2px;
}
QToolButton {
    background-color: transparent;
    color: #4c4f69;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 3px;
}
QToolButton:hover   { background-color: #dce0f4; border-color: #bcc0cc; }
QToolButton:pressed { background-color: #bcc0cc; }
QToolButton:checked {
    background-color: #dce0f4;
    border: 1px solid #1e66f5;
    color: #1e66f5;
}

/* ── Status / info labels ──────────────────────────────────────────────── */
QLabel#info  { color: #2e7d32; font-size: 10px; }
QLabel#warn  { color: #e65100; font-size: 10px; }
QLabel#muted { color: #9ca0b0; font-size: 10px; }

/* ── Accent buttons ────────────────────────────────────────────────────── */
QPushButton#btn_load {
    background-color: #dce0f4; color: #1e66f5;
    border: 1px solid #1e66f5; border-radius: 5px;
    padding: 6px 14px; font-weight: bold; font-size: 11px;
}
QPushButton#btn_load:hover   { background-color: #1e66f5; color: #eff1f5; }
QPushButton#btn_load:pressed { background-color: #0a50e0; color: #eff1f5; }

QPushButton#btn_action {
    background-color: #1e66f5; color: #eff1f5;
    border: none; border-radius: 5px;
    padding: 8px; font-weight: bold; font-size: 12px;
}
QPushButton#btn_action:hover    { background-color: #3576f5; }
QPushButton#btn_action:pressed  { background-color: #0a50e0; }
QPushButton#btn_action:disabled { background-color: #e6e9ef; color: #bcc0cc; }

QPushButton#btn_save {
    background-color: #40a02b; color: #eff1f5;
    border: none; border-radius: 5px;
    padding: 7px; font-weight: bold; font-size: 11px;
}
QPushButton#btn_save:hover    { background-color: #34862a; }
QPushButton#btn_save:pressed  { background-color: #286e21; }
QPushButton#btn_save:disabled { background-color: #e6e9ef; color: #bcc0cc; }

QPushButton#btn_spec {
    background-color: #8839ef; color: #eff1f5;
    border: none; border-radius: 5px;
    padding: 8px; font-weight: bold; font-size: 12px;
}
QPushButton#btn_spec:hover    { background-color: #7028d4; }
QPushButton#btn_spec:pressed  { background-color: #5a20ad; }
QPushButton#btn_spec:disabled { background-color: #e6e9ef; color: #bcc0cc; }

/* ── File list scroll area ─────────────────────────────────────────────── */
QScrollArea#file_list {
    border: 1px solid #ccd0da; border-radius: 4px; background: #ffffff;
}

/* ── File row frames ───────────────────────────────────────────────────── */
QFrame#file_row { background: #e8eaf6; border-radius: 4px; }
QFrame#file_row:hover { background: #dce0f4; }
"""


def save_img_btn_style(dark: bool) -> str:
    """Style for the ⬇ save-image overlay button (top-right corner of canvas)."""
    if dark:
        return (
            "QPushButton {"
            "background-color:rgba(20,20,35,210); color:#f9e2af;"
            "border:1px solid #45475a; border-radius:4px;"
            "font-size:13px; font-weight:bold; padding:0px;}"
            "QPushButton:hover {background-color:#f9e2af; color:#1e1e2e; border-color:#f9e2af;}"
            "QPushButton:pressed {background-color:#fab387;}"
        )
    return (
        "QPushButton {"
        "background-color:rgba(220,224,244,210); color:#e65100;"
        "border:1px solid #bcc0cc; border-radius:4px;"
        "font-size:13px; font-weight:bold; padding:0px;}"
        "QPushButton:hover {background-color:#e65100; color:#eff1f5; border-color:#e65100;}"
        "QPushButton:pressed {background-color:#bf360c;}"
    )


def max_btn_style(dark: bool) -> str:
    """Style for the ⤡ maximize overlay button."""
    if dark:
        return (
            "QPushButton {"
            "background-color:rgba(20,20,35,210); color:#89b4fa;"
            "border:1px solid #45475a; border-radius:4px;"
            "font-size:13px; font-weight:bold; padding:0px;}"
            "QPushButton:hover {background-color:#89b4fa; color:#1e1e2e; border-color:#89b4fa;}"
            "QPushButton:pressed {background-color:#74c7ec;}"
        )
    return (
        "QPushButton {"
        "background-color:rgba(220,224,244,210); color:#1e66f5;"
        "border:1px solid #bcc0cc; border-radius:4px;"
        "font-size:13px; font-weight:bold; padding:0px;}"
        "QPushButton:hover {background-color:#1e66f5; color:#eff1f5; border-color:#1e66f5;}"
        "QPushButton:pressed {background-color:#0a50e0;}"
    )


def restore_btn_style(dark: bool) -> str:
    """Style for the ⤢ restore overlay button."""
    if dark:
        return (
            "QPushButton {"
            "background-color:rgba(20,20,35,210); color:#a6e3a1;"
            "border:1px solid #45475a; border-radius:4px;"
            "font-size:13px; font-weight:bold; padding:0px;}"
            "QPushButton:hover {background-color:#a6e3a1; color:#1e1e2e; border-color:#a6e3a1;}"
            "QPushButton:pressed {background-color:#94e2d5;}"
        )
    return (
        "QPushButton {"
        "background-color:rgba(220,224,244,210); color:#40a02b;"
        "border:1px solid #bcc0cc; border-radius:4px;"
        "font-size:13px; font-weight:bold; padding:0px;}"
        "QPushButton:hover {background-color:#40a02b; color:#eff1f5; border-color:#40a02b;}"
        "QPushButton:pressed {background-color:#34862a;}"
    )
