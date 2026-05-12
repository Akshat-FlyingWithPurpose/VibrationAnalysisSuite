"""
Raw Crop Tab — Python equivalent of RawCrop.m

Load a .bin file, drag the start/end trim bars on the time-domain plots
(all three axes stay in sync), fine-tune via the spin boxes, then crop.
"""
import os
import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QDoubleSpinBox, QSplitter, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt

from matplotlib.patches import Rectangle

from .bin_io import read_bin, write_bin, NUM_IMUS, IMU_NAMES
from . import plot_utils
from .plot_utils import make_canvas, style_axes, placeholder_axes, retheme_axes, AXIS_COLORS
from .styles import save_img_btn_style


# Pixel grab radius — how close the mouse must be to a trim bar to grab it
_GRAB_PX = 8

# One distinct colour per IMU (visible on both light and dark backgrounds)
_IMU_COLORS = ['#1565c0', '#e53935', '#2e7d32', '#e65100']
_IMU_ALPHAS = [0.90, 0.85, 0.85, 0.80]


class CropTab(QWidget):
    def __init__(self, log_fn, add_to_fft_fn=None):
        super().__init__()
        self._log           = log_fn
        self._add_to_fft_fn = add_to_fft_fn
        self._data          = None
        self._filepath      = None

        # Trim-bar state
        self._trim_axes        = []   # 3 Axes objects
        self._trim_start_lines = []   # 3 Line2D  (green bar)
        self._trim_end_lines   = []   # 3 Line2D  (red bar)
        self._trim_spans       = []   # 3 Polygon (filled selection)
        self._drag_which       = None # 'start' | 'end' | None
        self._cids             = []   # mpl event connection IDs
        self._updating_trim    = False  # guard against spin↔bar feedback loops

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
        ctrl.setFixedWidth(250)
        cl = QVBoxLayout(ctrl)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.setSpacing(10)

        # File group
        fg = QGroupBox("File")
        fl = QVBoxLayout(fg)

        self.btn_load = QPushButton("Load BIN File")
        self.btn_load.setObjectName("btn_load")
        self.btn_load.clicked.connect(self._load_file)
        fl.addWidget(self.btn_load)

        self.lbl_file = QLabel("No file loaded")
        self.lbl_file.setObjectName("muted")
        self.lbl_file.setWordWrap(True)
        fl.addWidget(self.lbl_file)

        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("info")
        self.lbl_info.setWordWrap(True)
        fl.addWidget(self.lbl_info)

        cl.addWidget(fg)

        # Crop range group
        cg = QGroupBox("Crop Range")
        cl2 = QVBoxLayout(cg)

        cl2.addWidget(QLabel("Start Time (s):"))
        self.spin_start = QDoubleSpinBox()
        self.spin_start.setDecimals(3)
        self.spin_start.setSingleStep(0.1)
        self.spin_start.setEnabled(False)
        self.spin_start.valueChanged.connect(self._on_spin_changed)
        cl2.addWidget(self.spin_start)

        cl2.addWidget(QLabel("End Time (s):"))
        self.spin_end = QDoubleSpinBox()
        self.spin_end.setDecimals(3)
        self.spin_end.setSingleStep(0.1)
        self.spin_end.setEnabled(False)
        self.spin_end.valueChanged.connect(self._on_spin_changed)
        cl2.addWidget(self.spin_end)

        # Live selection info
        self.lbl_selection = QLabel("")
        self.lbl_selection.setObjectName("info")
        self.lbl_selection.setWordWrap(True)
        cl2.addWidget(self.lbl_selection)

        cl.addWidget(cg)

        # Export group
        eg = QGroupBox("Export")
        el = QVBoxLayout(eg)

        self.btn_save = QPushButton("Crop && Save")
        self.btn_save.setObjectName("btn_save")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_cropped)
        el.addWidget(self.btn_save)

        self.lbl_crop_info = QLabel("")
        self.lbl_crop_info.setObjectName("warn")
        self.lbl_crop_info.setWordWrap(True)
        el.addWidget(self.lbl_crop_info)

        cl.addWidget(eg)
        cl.addStretch()

        splitter.addWidget(ctrl)

        # ── Right: plot ─────────────────────────────────────────────────────
        plot_w = QWidget()
        pl = QVBoxLayout(plot_w)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(0)

        self.fig, self.canvas, self.toolbar = make_canvas(plot_w)
        pl.addWidget(self.toolbar)
        pl.addWidget(self.canvas)

        splitter.addWidget(plot_w)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # ── Save-image overlay button (always visible, top-right of canvas) ────
        self._save_img_btn = QPushButton("⬇", self.canvas)
        self._save_img_btn.setFixedSize(24, 24)
        self._save_img_btn.setToolTip("Save plot image to ~/Downloads/VibeResults")
        self._save_img_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_img_btn.setStyleSheet(save_img_btn_style(plot_utils._dark))
        self._save_img_btn.clicked.connect(self._save_plot_image)
        self._save_img_btn.show()
        self._save_img_btn.raise_()
        self.canvas.mpl_connect('resize_event', lambda _e: self._position_save_btn())

        placeholder_axes(self.fig, "Load a .bin file to inspect and crop.")
        self.canvas.draw()

    # ─────────────────────────────────────────────────────────────────────────
    # Plot helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _plot_data(self, data: dict, subtitle: str = ""):
        """Render time-domain signals (all 4 IMUs) and install draggable trim bars."""
        t         = data['time_s']
        sigs      = [data['accX'], data['accY'], data['accZ']]  # each: list of 4 arrays
        labels    = ['AccX', 'AccY', 'AccZ']
        axes_keys = list(AXIS_COLORS.keys())   # ['X', 'Y', 'Z']

        t_start = self.spin_start.value() if self.spin_start.isEnabled() else t[0]
        t_end   = self.spin_end.value()   if self.spin_end.isEnabled()   else t[-1]
        t_start = max(t[0], min(t[-1], t_start))
        t_end   = max(t[0], min(t[-1], t_end))

        self._disconnect_events()
        self._trim_axes.clear()
        self._trim_start_lines.clear()
        self._trim_end_lines.clear()
        self._trim_spans.clear()

        self.fig.clear()
        self.fig.patch.set_facecolor(plot_utils.FIG_BG)

        for i, (sig_all, lbl, axis) in enumerate(zip(sigs, labels, axes_keys)):
            ax = self.fig.add_subplot(3, 1, i + 1)
            style_axes(ax, title=f"{lbl}  {subtitle}",
                       xlabel='Time (s)', ylabel='Acceleration (m/s\u00b2)',
                       title_color=AXIS_COLORS[axis])
            # Plot all 4 IMUs on this subplot
            for imu_idx in range(NUM_IMUS):
                ax.plot(t, sig_all[imu_idx],
                        color=_IMU_COLORS[imu_idx],
                        linewidth=0.7, alpha=_IMU_ALPHAS[imu_idx],
                        label=IMU_NAMES[imu_idx])
            ax.legend(fontsize=7, loc='upper right')

            # Filled span for selected region — Rectangle is easier to update
            # than axvspan's Polygon; x-transform=data, y-transform=axes (0-1)
            span = Rectangle(
                (t_start, 0), t_end - t_start, 1,
                transform=ax.get_xaxis_transform(),
                color='#a6e3a1', alpha=0.13, zorder=1, lw=0,
            )
            ax.add_patch(span)

            # Start bar (green) and end bar (red)
            sl = ax.axvline(t_start, color='#a6e3a1', linewidth=2.0,
                            linestyle='--', alpha=0.95, zorder=3)
            el = ax.axvline(t_end,   color='#f38ba8', linewidth=2.0,
                            linestyle='--', alpha=0.95, zorder=3)

            self._trim_axes.append(ax)
            self._trim_spans.append(span)
            self._trim_start_lines.append(sl)
            self._trim_end_lines.append(el)

        self.fig.tight_layout(pad=1.5)
        self._connect_events()
        self.canvas.draw()
        self._refresh_selection_label()

    def _update_trim_display(self, t_start: float, t_end: float):
        """Move all trim bars + spans to new positions, then redraw."""
        for sl, el, span in zip(
                self._trim_start_lines, self._trim_end_lines, self._trim_spans):
            sl.set_xdata([t_start, t_start])
            el.set_xdata([t_end,   t_end])
            span.set_x(t_start)
            span.set_width(t_end - t_start)
        self.canvas.draw()

    def _refresh_selection_label(self):
        """Update the live 'N records selected' info label."""
        if self._data is None:
            return
        t_start = self.spin_start.value()
        t_end   = self.spin_end.value()
        t       = self._data['time_s']
        n       = int(np.sum((t >= t_start) & (t <= t_end)))
        dur     = max(0.0, t_end - t_start)
        self.lbl_selection.setText(
            f"{n} records selected\n"
            f"{t_start:.3f} – {t_end:.3f} s  ({dur:.3f} s)"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Trim-bar mouse events
    # ─────────────────────────────────────────────────────────────────────────

    def _connect_events(self):
        self._cids = [
            self.canvas.mpl_connect('button_press_event',   self._on_trim_press),
            self.canvas.mpl_connect('motion_notify_event',  self._on_trim_motion),
            self.canvas.mpl_connect('button_release_event', self._on_trim_release),
        ]

    def _disconnect_events(self):
        for cid in self._cids:
            self.canvas.mpl_disconnect(cid)
        self._cids.clear()
        self._drag_which = None

    def _bar_disp_x(self, ax, data_x: float) -> float:
        """Convert a data-x value to canvas pixel x for the given axes."""
        return ax.transData.transform((data_x, 0))[0]

    def _on_trim_press(self, event):
        if event.button != 1 or event.inaxes not in self._trim_axes:
            return
        if self.toolbar.mode != '':   # zoom/pan takes priority
            return

        ax = event.inaxes
        t_start = self.spin_start.value()
        t_end   = self.spin_end.value()

        ds = abs(self._bar_disp_x(ax, t_start) - event.x)
        de = abs(self._bar_disp_x(ax, t_end)   - event.x)

        if ds <= _GRAB_PX and ds <= de:
            self._drag_which = 'start'
        elif de <= _GRAB_PX:
            self._drag_which = 'end'
        else:
            self._drag_which = None

    def _on_trim_motion(self, event):
        # ── Cursor feedback when not dragging ─────────────────────────────
        if self._drag_which is None:
            if event.inaxes in self._trim_axes and event.xdata is not None:
                ax  = event.inaxes
                ds  = abs(self._bar_disp_x(ax, self.spin_start.value()) - event.x)
                de  = abs(self._bar_disp_x(ax, self.spin_end.value())   - event.x)
                if ds <= _GRAB_PX or de <= _GRAB_PX:
                    self.canvas.setCursor(Qt.CursorShape.SizeHorCursor)
                    return
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor)
            return

        # ── Active drag ───────────────────────────────────────────────────
        if event.inaxes not in self._trim_axes or event.xdata is None:
            return

        t     = self._data['time_s']
        x     = float(np.clip(event.xdata, t[0], t[-1]))
        t_start = self.spin_start.value()
        t_end   = self.spin_end.value()

        self._updating_trim = True
        if self._drag_which == 'start':
            x = min(x, t_end - 0.001)
            self.spin_start.setValue(x)
            t_start = x
        else:
            x = max(x, t_start + 0.001)
            self.spin_end.setValue(x)
            t_end = x
        self._updating_trim = False

        self._update_trim_display(t_start, t_end)
        self._refresh_selection_label()

    def _on_trim_release(self, event):
        if self._drag_which is not None:
            self._drag_which = None
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor)

    # ─────────────────────────────────────────────────────────────────────────
    # Spin-box → trim bar sync
    # ─────────────────────────────────────────────────────────────────────────

    def _on_spin_changed(self):
        """Move trim bars when the user edits a spin box directly."""
        if self._updating_trim or self._data is None or not self._trim_axes:
            return
        self._update_trim_display(self.spin_start.value(), self.spin_end.value())
        self._refresh_selection_label()

    # ─────────────────────────────────────────────────────────────────────────
    # Slots
    # ─────────────────────────────────────────────────────────────────────────

    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select BIN File", "", "BIN Files (*.bin)")
        if not path:
            return

        try:
            self._data     = read_bin(path)
            self._filepath = path
        except Exception as e:
            self._log(f"[Crop] Error loading file: {e}")
            return

        fname = os.path.basename(path)
        d     = self._data
        t     = d['time_s']

        self.lbl_file.setText(fname)
        self.lbl_info.setText(
            f"Records : {d['num_records']}\n"
            f"Duration: {t[0]:.3f} – {t[-1]:.3f} s\n"
            f"Fs      : ~{d['Fs']:.1f} Hz"
        )

        # Configure spin boxes (block signals to avoid spurious updates)
        for spin, val in [(self.spin_start, t[0]), (self.spin_end, t[-1])]:
            spin.blockSignals(True)
            spin.setRange(t[0], t[-1])
            spin.setValue(val)
            spin.blockSignals(False)
            spin.setEnabled(True)

        self.btn_save.setEnabled(True)
        self.lbl_crop_info.setText("")

        self._plot_data(d, "— Full Data")
        self._log(f"[Crop] Loaded '{fname}' — {d['num_records']} records, "
                  f"{t[0]:.3f}–{t[-1]:.3f} s, Fs≈{d['Fs']:.1f} Hz")

    def _get_crop_mask(self):
        t_start = self.spin_start.value()
        t_end   = self.spin_end.value()
        if t_start >= t_end:
            self._log("[Crop] Start time must be less than End time.")
            return None, None, None
        t    = self._data['time_s']
        mask = (t >= t_start) & (t <= t_end)
        if not np.any(mask):
            self._log("[Crop] No records in the selected range.")
            return None, None, None
        return mask, t_start, t_end

    def _save_cropped(self):
        if self._data is None:
            return
        mask, t_start, t_end = self._get_crop_mask()
        if mask is None:
            return

        n_crop   = int(np.sum(mask))
        base, _  = os.path.splitext(os.path.basename(self._filepath))
        default  = f"{base}_crop_{t_start:.1f}-{t_end:.1f}s.bin"
        dest_dir = os.path.dirname(self._filepath)

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Cropped BIN File",
            os.path.join(dest_dir, default),
            "BIN Files (*.bin)")
        if not save_path:
            return

        d = self._data
        try:
            write_bin(
                save_path,
                d['time_us'][mask],
                [d['accX'][i][mask] for i in range(NUM_IMUS)],
                [d['accY'][i][mask] for i in range(NUM_IMUS)],
                [d['accZ'][i][mask] for i in range(NUM_IMUS)],
                d.get('start_epoch', 0),
            )
        except Exception as e:
            self._log(f"[Crop] Error saving file: {e}")
            return

        self.lbl_crop_info.setText(
            f"Saved: {os.path.basename(save_path)}\n{n_crop} records")
        self._log(f"[Crop] Saved {n_crop} records → {os.path.basename(save_path)}")

        # ── Offer to add the cropped file to FFT Analyzer ─────────────────
        if self._add_to_fft_fn is not None:
            reply = QMessageBox.question(
                self,
                "Add to FFT Analyzer?",
                f"<b>{os.path.basename(save_path)}</b> was saved successfully.<br><br>"
                "Would you like to add it to the <b>FFT Analyzer</b> tab?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._add_to_fft_fn(save_path)
                self._log("[Crop] Added cropped file to FFT Analyzer.")

    # ─────────────────────────────────────────────────────────────────────────
    # Save plot image
    # ─────────────────────────────────────────────────────────────────────────

    def _position_save_btn(self):
        """Pin the save button to the top-right corner of the canvas."""
        cw = self.canvas.width()
        if cw > 0:
            margin = 6
            self._save_img_btn.move(cw - self._save_img_btn.width() - margin, margin)
            self._save_img_btn.raise_()

    def _save_plot_image(self):
        from .plot_utils import save_figure
        try:
            path = save_figure(self.fig, "Crop")
            self._log(f"[Crop] Image saved → {path}")
        except Exception as e:
            self._log(f"[Crop] Error saving image: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Theme
    # ─────────────────────────────────────────────────────────────────────────

    def redraw_theme(self):
        """Repaint axes colours in-place — preserves zoom, pan, trim bars."""
        self.fig.patch.set_facecolor(plot_utils.FIG_BG)
        self._save_img_btn.setStyleSheet(save_img_btn_style(plot_utils._dark))
        if not self._trim_axes:
            placeholder_axes(self.fig, "Load a .bin file to inspect and crop.")
            self.canvas.draw()
            return
        for ax, axis in zip(self._trim_axes, AXIS_COLORS.keys()):
            retheme_axes(ax, title_color=AXIS_COLORS[axis])
        self.canvas.draw_idle()
