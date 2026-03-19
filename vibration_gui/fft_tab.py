"""
FFT Analyzer Tab — Python equivalent of VibeDriver.m

Load multiple .bin files, overlay smoothed FFT (X / Y / Z) and
time-domain signals, one colour per file.

Per-file checkboxes toggle visibility with instant redraw.
Each subplot has a ⤢ maximize button; maximized view has a ⤡ restore button.
"""
import os
import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QDoubleSpinBox, QSpinBox,
    QSplitter, QFileDialog, QCheckBox, QScrollArea, QFrame, QToolButton,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .bin_io import read_bin
from .analysis import compute_fft
from . import plot_utils
from .plot_utils import (
    make_canvas, style_axes, placeholder_axes, add_legend,
    retheme_axes, AXIS_COLORS,
)
from .styles import max_btn_style, restore_btn_style

# Fixed colour palette — one colour per file slot (cycles after 10)
_PALETTE = [
    '#89b4fa', '#f38ba8', '#a6e3a1', '#fab387',
    '#cba6f7', '#89dceb', '#f9e2af', '#94e2d5',
    '#eba0ac', '#b4befe',
]



class FFTTab(QWidget):
    def __init__(self, log_fn):
        super().__init__()
        self._log      = log_fn
        self._files    = []      # list of dicts: {path, data, color, chk, row_w}
        self._analyzed = False   # True once Analyze has been clicked at least once

        # Maximize-overlay state
        self._max_btns         = []   # QPushButton overlays currently shown
        self._axes_for_btns    = []   # axes parallel to _max_btns
        self._current_axes_dict = {}  # axes dict saved after last _draw()
        self._maximized_key    = None # None = grid view; 'fft_X' etc. = single-plot

        # Data-cursor state: maps axes → (annotation, marker)
        self._data_cursors: dict = {}

        self._setup_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # UI Setup
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # ── Left: controls ──────────────────────────────────────────────────
        ctrl = QWidget()
        ctrl.setFixedWidth(270)
        cl = QVBoxLayout(ctrl)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.setSpacing(10)

        # ── File group ───────────────────────────────────────────────────────
        fg = QGroupBox("Files")
        fl = QVBoxLayout(fg)
        fl.setSpacing(6)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("Add Files")
        self.btn_add.setObjectName("btn_load")
        self.btn_add.clicked.connect(self._add_files)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self._clear_files)

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_clear)
        fl.addLayout(btn_row)

        # Scroll area that holds the per-file rows
        self._rows_widget = QWidget()
        self._rows_widget.setStyleSheet("background: transparent;")
        self._rows_layout = QVBoxLayout(self._rows_widget)
        self._rows_layout.setContentsMargins(0, 2, 0, 2)
        self._rows_layout.setSpacing(3)
        self._rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll = QScrollArea()
        scroll.setWidget(self._rows_widget)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(150)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("file_list")
        fl.addWidget(scroll)

        self.lbl_file_count = QLabel("No files loaded")
        self.lbl_file_count.setObjectName("muted")
        fl.addWidget(self.lbl_file_count)

        cl.addWidget(fg)

        # ── FFT Settings ─────────────────────────────────────────────────────
        sg = QGroupBox("FFT Settings")
        sl = QVBoxLayout(sg)

        sl.addWidget(QLabel("Smoothing Window:"))
        self.spin_smooth = QSpinBox()
        self.spin_smooth.setRange(1, 200)
        self.spin_smooth.setValue(10)
        self.spin_smooth.setToolTip("Moving-average window applied to FFT magnitude")
        sl.addWidget(self.spin_smooth)

        self.chk_auto_ylim = QCheckBox("Auto Y-limit (1.3× peak)")
        self.chk_auto_ylim.setChecked(True)
        sl.addWidget(self.chk_auto_ylim)

        sl.addWidget(QLabel("Y-Axis Limit (if not auto):"))
        self.spin_ylim = QDoubleSpinBox()
        self.spin_ylim.setRange(0.0, 100000.0)
        self.spin_ylim.setValue(0.5)
        self.spin_ylim.setDecimals(3)
        self.spin_ylim.setSingleStep(0.05)
        sl.addWidget(self.spin_ylim)

        self.chk_log_freq = QCheckBox("Log frequency scale")
        sl.addWidget(self.chk_log_freq)

        sl.addWidget(QLabel("Frequency Range (Hz):"))
        freq_row = QHBoxLayout()
        self.spin_fmin = QDoubleSpinBox()
        self.spin_fmin.setRange(0, 100000)
        self.spin_fmin.setValue(0.0)
        self.spin_fmin.setDecimals(1)
        self.spin_fmax = QDoubleSpinBox()
        self.spin_fmax.setRange(0, 100000)
        self.spin_fmax.setValue(50.0)
        self.spin_fmax.setDecimals(1)
        freq_row.addWidget(self.spin_fmin)
        freq_row.addWidget(QLabel("–"))
        freq_row.addWidget(self.spin_fmax)
        sl.addLayout(freq_row)

        cl.addWidget(sg)

        # ── Show Plots ───────────────────────────────────────────────────────
        vg = QGroupBox("Show Plots")
        vl = QVBoxLayout(vg)

        self.chk_fft  = QCheckBox("FFT (Frequency Domain)")
        self.chk_fft.setChecked(True)
        self.chk_time = QCheckBox("Time Domain")
        self.chk_time.setChecked(True)
        vl.addWidget(self.chk_fft)
        vl.addWidget(self.chk_time)

        cl.addWidget(vg)

        # ── Analyze button ───────────────────────────────────────────────────
        self.btn_analyze = QPushButton("Analyze")
        self.btn_analyze.setObjectName("btn_action")
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.clicked.connect(self._analyze)
        cl.addWidget(self.btn_analyze)

        cl.addStretch()
        splitter.addWidget(ctrl)

        # ── Right: plot canvas ───────────────────────────────────────────────
        plot_w = QWidget()
        pl = QVBoxLayout(plot_w)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(0)

        self.fig, self.canvas, self.toolbar = make_canvas(plot_w)

        # ── Data-cursor toggle button in the toolbar ─────────────────────────
        self.toolbar.addSeparator()
        self._cursor_btn = QToolButton()
        self._cursor_btn.setText("⌖")
        self._cursor_btn.setFont(QFont("Segoe UI", 13))
        self._cursor_btn.setFixedSize(32, 28)
        self._cursor_btn.setCheckable(True)
        self._cursor_btn.setChecked(False)
        self._cursor_btn.setToolTip(
            "Data Cursor\n"
            "When active: left-click any FFT plot to snap to the nearest\n"
            "data point and read its frequency & magnitude.\n"
            "Right-click a tip to dismiss it."
        )
        self._cursor_btn.toggled.connect(self._on_cursor_mode_toggled)
        self.toolbar.addWidget(self._cursor_btn)

        pl.addWidget(self.toolbar)
        pl.addWidget(self.canvas)

        # Reposition overlay buttons whenever the canvas is resized
        self.canvas.mpl_connect('resize_event',
                                lambda _e: self._reposition_buttons())
        # Data cursor — click on FFT plots to read off (freq, magnitude)
        self.canvas.mpl_connect('button_press_event', self._on_canvas_click)

        splitter.addWidget(plot_w)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        placeholder_axes(self.fig, "Add .bin files and click Analyze.")
        self.canvas.draw()

    # ─────────────────────────────────────────────────────────────────────────
    # Per-file row widget
    # ─────────────────────────────────────────────────────────────────────────

    def _make_file_row(self, fname: str, filepath: str, color: str):
        """
        Build one file row:  [● swatch]  [filename]  [checkbox]
        Returns (row_widget, checkbox).
        """
        row_w = QFrame()
        row_w.setFrameShape(QFrame.Shape.NoFrame)
        row_w.setObjectName("file_row")
        row_w.setFixedHeight(28)

        hl = QHBoxLayout(row_w)
        hl.setContentsMargins(6, 0, 6, 0)
        hl.setSpacing(7)

        swatch = QLabel()
        swatch.setFixedSize(11, 11)
        swatch.setStyleSheet(
            f"background-color:{color}; border-radius:5px; border:none;"
        )

        max_chars = 26
        if len(fname) > max_chars:
            half = (max_chars - 1) // 2
            display = fname[:half] + "\u2026" + fname[-(max_chars - half - 1):]
        else:
            display = fname
        name_lbl = QLabel(display)
        name_lbl.setToolTip(filepath)
        name_lbl.setStyleSheet("font-size:11px; background:transparent;")
        name_lbl.setFont(QFont("Segoe UI", 10))

        chk = QCheckBox()
        chk.setChecked(True)
        chk.setToolTip("Show / hide this file in the plots")

        hl.addWidget(swatch)
        hl.addWidget(name_lbl, stretch=1)
        hl.addWidget(chk)

        return row_w, chk

    # ─────────────────────────────────────────────────────────────────────────
    # Overlay maximize / restore buttons
    # ─────────────────────────────────────────────────────────────────────────

    def _clear_overlay_buttons(self):
        for btn in self._max_btns:
            btn.hide()
            btn.deleteLater()
        self._max_btns      = []
        self._axes_for_btns = []

    def _make_overlay_btn(self, text: str, style: str, callback) -> QPushButton:
        """Create a small QPushButton parented directly to the canvas widget."""
        btn = QPushButton(text, self.canvas)
        btn.setFixedSize(24, 24)
        btn.setStyleSheet(style)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        btn.show()
        btn.raise_()
        return btn

    def _place_overlay_buttons(self):
        """
        After every draw, create/recreate the maximize (or restore) buttons
        and position them over the correct axes corners.
        """
        self._clear_overlay_buttons()

        if self._maximized_key is not None:
            # Single axes — show one restore button
            axes = list(self._current_axes_dict.values())
            if axes:
                btn = self._make_overlay_btn(
                    "\u2922",          # ⤢  four-corner arrows out → restore
                    restore_btn_style(plot_utils._dark),
                    self._restore,
                )
                btn.setToolTip("Restore all plots")
                self._max_btns      = [btn]
                self._axes_for_btns = axes
        else:
            # Grid view — one maximize button per axes
            for key, ax in self._current_axes_dict.items():
                # capture key in default-arg to avoid late-binding closure bug
                btn = self._make_overlay_btn(
                    "\u2921",          # ⤡  four-corner arrows in → maximize
                    max_btn_style(plot_utils._dark),
                    lambda _checked, k=key: self._maximize(k),
                )
                btn.setToolTip("Maximize this plot")
                self._max_btns.append(btn)
                self._axes_for_btns.append(ax)

        self._reposition_buttons()

    def _reposition_buttons(self):
        """Move each overlay button to the top-right corner of its axes."""
        if not self._max_btns:
            return

        canvas_h = self.canvas.height()

        # Try to get a renderer; fall back gracefully
        try:
            renderer = self.fig.canvas.get_renderer()
        except Exception:
            renderer = None

        for btn, ax in zip(self._max_btns, self._axes_for_btns):
            try:
                bbox = (ax.get_window_extent(renderer=renderer)
                        if renderer else ax.get_window_extent())
                # top-right corner in Qt coordinates (y=0 at top)
                btn_x = int(bbox.x1) - 28   # 28 = 24px btn + 4px margin
                btn_y = int(canvas_h - bbox.y1) + 4  # 4px inside top edge
                btn.move(max(0, btn_x), max(0, btn_y))
                btn.raise_()
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # Maximize / restore
    # ─────────────────────────────────────────────────────────────────────────

    def _maximize(self, key: str):
        """Redraw a single axes (key e.g. 'fft_X') filling the whole canvas."""
        self._maximized_key = key
        self._draw_single(key)

    def _restore(self):
        """Return to the full grid view."""
        self._maximized_key = None
        self._draw(log=False)

    def _draw_single(self, key: str):
        """Draw one plot full-size, with a restore button overlay."""
        active = [f for f in self._files if f['chk'].isChecked()]
        if not active:
            placeholder_axes(self.fig, "No files selected.")
            self.canvas.draw()
            self._clear_overlay_buttons()
            return

        plot_type, axis = key.split('_', 1)   # 'fft' | 'time',  'X' | 'Y' | 'Z'
        smooth_win  = self.spin_smooth.value()
        ylim_fft    = self.spin_ylim.value()
        log_freq    = self.chk_log_freq.isChecked()
        auto_ylim   = self.chk_auto_ylim.isChecked()

        self._clear_data_cursors()
        self.fig.clear()
        self.fig.patch.set_facecolor(plot_utils.FIG_BG)

        ax = self.fig.add_subplot(1, 1, 1)
        if plot_type == 'fft':
            style_axes(ax,
                       title=f"FFT \u2014 Acc{axis}",
                       xlabel='Frequency (Hz)', ylabel='|FFT| (g)',
                       title_color=AXIS_COLORS[axis])
        else:
            style_axes(ax,
                       title=f"Time Domain \u2014 Acc{axis}",
                       xlabel='Time (s)', ylabel='Acceleration (g)',
                       title_color=AXIS_COLORS[axis])

        max_peak = 0.0
        for entry in active:
            sig = entry['data'][f'acc{axis}_uniform']
            Fs  = entry['data']['Fs']
            lbl = os.path.basename(entry['path'])

            if plot_type == 'fft':
                f, _, sm = compute_fft(sig, Fs, smooth_win)
                ax.plot(f, sm, color=entry['color'], linewidth=1.2,
                        alpha=0.9, label=lbl)
                if auto_ylim:
                    max_peak = max(max_peak, sm.max())
                else:
                    ax.set_ylim(0, ylim_fft)
                if log_freq:
                    ax.set_xscale('log')
            else:
                ax.plot(entry['data']['time_uniform'], sig,
                        color=entry['color'], linewidth=0.9,
                        alpha=0.9, label=lbl)

        if plot_type == 'fft':
            if auto_ylim and max_peak > 0:
                ax.set_ylim(0, max_peak * 1.3)
            if not log_freq:
                ax.set_xlim(self.spin_fmin.value(), self.spin_fmax.value())

        add_legend(ax)
        self.fig.tight_layout(pad=1.5)
        self.canvas.draw()

        # Save axes dict (single entry) so _place_overlay_buttons finds it
        self._current_axes_dict = {key: ax}
        self._place_overlay_buttons()

    # ─────────────────────────────────────────────────────────────────────────
    # Data cursor
    # ─────────────────────────────────────────────────────────────────────────

    def _clear_data_cursors(self):
        """Remove all data-cursor annotations and markers from the figure."""
        for ann, marker in self._data_cursors.values():
            try:
                ann.remove()
            except Exception:
                pass
            try:
                marker.remove()
            except Exception:
                pass
        self._data_cursors.clear()

    def _on_cursor_mode_toggled(self, checked: bool):
        """Clear all data tips when the cursor mode is switched off."""
        if not checked:
            self._clear_data_cursors()
            self.canvas.draw_idle()

    def _on_canvas_click(self, event):
        """
        Left-click on an FFT axes → snap to nearest line point and show a
        data-tip (frequency + magnitude).  Right-click → dismiss that tip.
        Toolbar navigation modes (zoom/pan) take priority and are left alone.
        """
        # Only active when cursor mode button is checked
        if not self._cursor_btn.isChecked():
            return
        # Don't clash with zoom / pan toolbar modes
        if self.toolbar.mode != '':
            return

        ax = event.inaxes
        if ax is None:
            return

        # Identify which key (if any) this axes belongs to, and only act on FFT axes
        fft_ax_keys = {v: k for k, v in self._current_axes_dict.items()
                       if k.startswith('fft_')}
        if ax not in fft_ax_keys:
            return

        # Right-click → dismiss this axes' cursor
        if event.button == 3:
            if ax in self._data_cursors:
                ann, marker = self._data_cursors.pop(ax)
                ann.remove()
                marker.remove()
                self.canvas.draw_idle()
            return

        if event.button != 1 or event.xdata is None or event.ydata is None:
            return

        xclick, yclick = event.xdata, event.ydata

        # Normalise by current axes range so x and y distances are comparable
        xlim   = ax.get_xlim()
        ylim   = ax.get_ylim()
        xrange = (xlim[1] - xlim[0]) or 1.0
        yrange = (ylim[1] - ylim[0]) or 1.0

        best_dist  = np.inf
        best_x = best_y = None
        best_color = '#cdd6f4'

        for line in ax.get_lines():
            xdata = line.get_xdata()
            ydata = line.get_ydata()
            if len(xdata) == 0 or not line.get_visible():
                continue
            dists = np.hypot((xdata - xclick) / xrange,
                             (ydata - yclick) / yrange)
            idx = int(np.argmin(dists))
            if dists[idx] < best_dist:
                best_dist  = dists[idx]
                best_x     = float(xdata[idx])
                best_y     = float(ydata[idx])
                best_color = line.get_color()

        if best_x is None:
            return

        # Remove any existing cursor on this axes
        if ax in self._data_cursors:
            old_ann, old_marker = self._data_cursors[ax]
            old_ann.remove()
            old_marker.remove()

        # Decide text offset direction so the tip stays inside the axes
        x_frac = (best_x - xlim[0]) / xrange
        y_frac = (best_y - ylim[0]) / yrange
        dx = -65 if x_frac > 0.75 else 12
        dy = -40 if y_frac > 0.75 else 12

        ann = ax.annotate(
            f" f = {best_x:.3f} Hz\n |A| = {best_y:.5f} g",
            xy=(best_x, best_y),
            xytext=(dx, dy),
            textcoords='offset points',
            fontsize=8,
            color=plot_utils.CURSOR_TEXT,
            bbox=dict(
                boxstyle='round,pad=0.45',
                facecolor=plot_utils.CURSOR_BG,
                edgecolor=best_color,
                alpha=0.93,
                linewidth=1.3,
            ),
            arrowprops=dict(
                arrowstyle='-|>',
                color=best_color,
                lw=1.0,
                mutation_scale=8,
            ),
            zorder=10,
        )

        marker, = ax.plot(best_x, best_y, 'o',
                          color=best_color, markersize=5, zorder=11,
                          markeredgecolor='white', markeredgewidth=0.6)

        self._data_cursors[ax] = (ann, marker)
        self.canvas.draw_idle()

    # ─────────────────────────────────────────────────────────────────────────
    # Slots
    # ─────────────────────────────────────────────────────────────────────────

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select BIN Files", "", "BIN Files (*.bin)")
        for path in paths:
            self.load_file(path)

    def load_file(self, path: str):
        """
        Load a single .bin file into the FFT tab programmatically.
        Safe to call from outside (e.g. after crop export).
        Does nothing silently if the file is already loaded.
        """
        if any(f['path'] == path for f in self._files):
            self._log(f"[FFT] '{os.path.basename(path)}' already loaded — skipped.")
            return

        try:
            data = read_bin(path)
        except Exception as e:
            self._log(f"[FFT] Error loading {os.path.basename(path)}: {e}")
            return

        fname  = os.path.basename(path)
        color  = _PALETTE[len(self._files) % len(_PALETTE)]
        row_w, chk = self._make_file_row(fname, path, color)
        chk.stateChanged.connect(self._on_visibility_changed)

        self._rows_layout.addWidget(row_w)
        self._files.append({
            'path':  path,
            'data':  data,
            'color': color,
            'chk':   chk,
            'row_w': row_w,
        })
        self._log(
            f"[FFT] Loaded '{fname}' "
            f"({data['num_records']} records, Fs\u2248{data['Fs']:.1f} Hz)"
        )

        n = len(self._files)
        self.lbl_file_count.setText(
            f"{n} file{'s' if n != 1 else ''} loaded" if n else "No files loaded"
        )
        self.btn_analyze.setEnabled(n > 0)

    def _clear_files(self):
        self._files.clear()
        self._analyzed      = False
        self._maximized_key = None
        self._current_axes_dict = {}

        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._clear_overlay_buttons()
        self.lbl_file_count.setText("No files loaded")
        self.btn_analyze.setEnabled(False)
        placeholder_axes(self.fig, "Add .bin files and click Analyze.")
        self.canvas.draw()
        self._log("[FFT] Cleared all files.")

    def _on_visibility_changed(self):
        if not self._analyzed:
            return
        if self._maximized_key is not None:
            self._draw_single(self._maximized_key)
        else:
            self._draw(log=False)

    def _analyze(self):
        """Full analyze — resets to grid view, enables real-time checkbox toggle."""
        self._maximized_key = None
        self._analyzed = True
        self._draw(log=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Core grid draw
    # ─────────────────────────────────────────────────────────────────────────

    def _draw(self, log: bool = True):
        show_fft  = self.chk_fft.isChecked()
        show_time = self.chk_time.isChecked()

        if not show_fft and not show_time:
            if log:
                self._log("[FFT] Please enable at least one plot type.")
            return

        active = [f for f in self._files if f['chk'].isChecked()]

        if not active:
            self._current_axes_dict = {}
            self._clear_overlay_buttons()
            self._clear_data_cursors()
            placeholder_axes(self.fig,
                             "No files selected \u2014 tick a checkbox to show.")
            self.canvas.draw()
            return

        smooth_win = self.spin_smooth.value()
        ylim_fft   = self.spin_ylim.value()
        log_freq   = self.chk_log_freq.isChecked()
        auto_ylim  = self.chk_auto_ylim.isChecked()
        fmin       = self.spin_fmin.value()
        fmax       = self.spin_fmax.value()

        n_cols = (1 if show_fft else 0) + (1 if show_time else 0)
        n_rows = 3

        self._clear_data_cursors()
        self.fig.clear()
        self.fig.patch.set_facecolor(plot_utils.FIG_BG)

        # Build axes grid
        axes = {}
        for row, axis in enumerate(['X', 'Y', 'Z']):
            col = 0
            if show_fft:
                col += 1
                ax = self.fig.add_subplot(n_rows, n_cols, row * n_cols + col)
                style_axes(ax,
                           title=f"FFT \u2014 Acc{axis}",
                           xlabel='Frequency (Hz)', ylabel='|FFT| (g)',
                           title_color=AXIS_COLORS[axis])
                axes[f'fft_{axis}'] = ax

            if show_time:
                col += 1
                ax = self.fig.add_subplot(n_rows, n_cols, row * n_cols + col)
                style_axes(ax,
                           title=f"Time Domain \u2014 Acc{axis}",
                           xlabel='Time (s)', ylabel='Acceleration (g)',
                           title_color=AXIS_COLORS[axis])
                axes[f'time_{axis}'] = ax

        # Track per-axis peaks for auto ylim
        max_peaks = {'X': 0.0, 'Y': 0.0, 'Z': 0.0}

        # Plot data
        for entry in active:
            color = entry['color']
            fname = os.path.basename(entry['path'])
            t     = entry['data']['time_uniform']
            Fs    = entry['data']['Fs']
            sigs  = {
                'X': entry['data']['accX_uniform'],
                'Y': entry['data']['accY_uniform'],
                'Z': entry['data']['accZ_uniform'],
            }

            for axis, sig in sigs.items():
                if show_fft:
                    f, _, sm = compute_fft(sig, Fs, smooth_win)
                    ax = axes[f'fft_{axis}']
                    ax.plot(f, sm, color=color, linewidth=0.9,
                            alpha=0.85, label=fname)
                    if auto_ylim:
                        max_peaks[axis] = max(max_peaks[axis], sm.max())
                    else:
                        ax.set_ylim(0, ylim_fft)
                    if log_freq:
                        ax.set_xscale('log')

                if show_time:
                    ax = axes[f'time_{axis}']
                    ax.plot(t, sig, color=color, linewidth=0.7,
                            alpha=0.8, label=fname)

            if log:
                self._log(f"[FFT] Processed '{fname}' (Fs\u2248{Fs:.1f} Hz)")

        # Apply auto ylim and freq range after all files are plotted
        if show_fft:
            for axis in ['X', 'Y', 'Z']:
                if f'fft_{axis}' in axes:
                    ax = axes[f'fft_{axis}']
                    if auto_ylim and max_peaks[axis] > 0:
                        ax.set_ylim(0, max_peaks[axis] * 1.3)
                    if not log_freq:
                        ax.set_xlim(fmin, fmax)

        for ax in axes.values():
            add_legend(ax)

        self.fig.tight_layout(pad=1.5)
        self.canvas.draw()

        # Save axes dict and place maximize buttons
        self._current_axes_dict = axes
        self._place_overlay_buttons()

        if log:
            n_active = len(active)
            n_total  = len(self._files)
            self._log(
                f"[FFT] Done \u2014 {n_active}/{n_total} file(s) shown."
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Theme
    # ─────────────────────────────────────────────────────────────────────────

    def redraw_theme(self):
        """Repaint axes colours in-place — preserves zoom, pan, selections."""
        self.fig.patch.set_facecolor(plot_utils.FIG_BG)
        if not self._current_axes_dict:
            placeholder_axes(self.fig, "Add .bin files and click Analyze.")
            self.canvas.draw()
            return
        for key, ax in self._current_axes_dict.items():
            axis = key.split('_')[1]          # 'X' | 'Y' | 'Z'
            retheme_axes(ax, title_color=AXIS_COLORS[axis])
        self._clear_data_cursors()            # tips use theme colours; stale after switch
        self._place_overlay_buttons()         # refresh overlay button styles
        self.canvas.draw_idle()
