"""
Spectrogram Tab — white-hot spectrogram for a selected IMU and axis.
Supports 4-IMU .bin files; IMU (1-4) and axis (X/Y/Z) are selectable
via a nav bar above the canvas.
"""
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QDoubleSpinBox, QSpinBox,
    QSplitter, QFileDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from .bin_io import read_bin, NUM_IMUS, IMU_NAMES
from .analysis import compute_spectrogram, make_whitehot_colormap
from . import plot_utils
from .plot_utils import make_canvas, placeholder_axes
from .styles import save_img_btn_style


# ─────────────────────────────────────────────────────────────────────────────
# Background worker — keeps GUI responsive during heavy scipy computation
# ─────────────────────────────────────────────────────────────────────────────

class _SpectrogramWorker(QThread):
    done  = pyqtSignal(object, object, object)   # F, T, mag_lin
    error = pyqtSignal(str)

    def __init__(self, acc, Fs, window, noverlap, nfft):
        super().__init__()
        self._acc     = acc
        self._Fs      = Fs
        self._window  = window
        self._noverlap = noverlap
        self._nfft    = nfft

    def run(self):
        try:
            F, T, mag_lin = compute_spectrogram(
                self._acc, self._Fs,
                window=self._window, noverlap=self._noverlap, nfft=self._nfft)
            self.done.emit(F, T, mag_lin)
        except Exception as e:
            self.error.emit(str(e))


class SpectrogramTab(QWidget):
    def __init__(self, log_fn):
        super().__init__()
        self._log           = log_fn
        self._data          = None
        self._filepath      = None
        self._analyzed      = False
        self._spec_ax       = None
        self._cbar          = None
        self._worker        = None
        self._pending       = {}
        self._spec_imu_idx  = 0   # 0-3
        self._spec_axis_idx = 0   # 0=X, 1=Y, 2=Z
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

        cl.addWidget(fg)

        spg = QGroupBox("Spectrogram")
        spl = QVBoxLayout(spg)

        spl.addWidget(QLabel("Window Size:"))
        self.spin_window = QSpinBox()
        self.spin_window.setRange(64, 16384)
        self.spin_window.setValue(1024)
        self.spin_window.setSingleStep(256)
        spl.addWidget(self.spin_window)

        spl.addWidget(QLabel("Magnitude Limit (m/s\u00b2):"))
        self.spin_mag_lim = QDoubleSpinBox()
        self.spin_mag_lim.setRange(0.0001, 100000.0)
        self.spin_mag_lim.setValue(11.77)   # ≈ 1.2 g in m/s²
        self.spin_mag_lim.setDecimals(4)
        self.spin_mag_lim.setSingleStep(0.05)
        spl.addWidget(self.spin_mag_lim)

        spl.addWidget(QLabel("Freq Range (Hz):"))
        sf_row = QHBoxLayout()
        self.spin_spec_fmin = QDoubleSpinBox()
        self.spin_spec_fmin.setRange(0, 100000)
        self.spin_spec_fmin.setValue(0.0)
        self.spin_spec_fmax = QDoubleSpinBox()
        self.spin_spec_fmax.setRange(0, 100000)
        self.spin_spec_fmax.setValue(40.0)
        sf_row.addWidget(self.spin_spec_fmin)
        sf_row.addWidget(QLabel("–"))
        sf_row.addWidget(self.spin_spec_fmax)
        spl.addLayout(sf_row)

        cl.addWidget(spg)

        self.btn_analyze = QPushButton("Analyze")
        self.btn_analyze.setObjectName("btn_spec")
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.clicked.connect(self._analyze)
        cl.addWidget(self.btn_analyze)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("info")
        self.lbl_status.setWordWrap(True)
        cl.addWidget(self.lbl_status)

        cl.addStretch()
        splitter.addWidget(ctrl)

        # ── Right: plot ─────────────────────────────────────────────────────
        plot_w = QWidget()
        pl = QVBoxLayout(plot_w)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(0)

        self.fig, self.canvas, self.toolbar = make_canvas(plot_w)

        # ── IMU + Axis navigation bar ────────────────────────────────────────
        nav_bar = QWidget()
        nav_bar.setFixedHeight(38)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(8, 4, 8, 4)
        nav_layout.setSpacing(4)

        from PyQt6.QtWidgets import QToolButton
        self._spec_imu_btns = []
        for i in range(NUM_IMUS):
            btn = QToolButton()
            btn.setText(IMU_NAMES[i])
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setMinimumWidth(64)
            btn.setToolTip(f"Use {IMU_NAMES[i]} for spectrogram")
            btn.clicked.connect(lambda _, idx=i: self._select_imu(idx))
            self._spec_imu_btns.append(btn)

        sep = QLabel("│")
        sep.setFixedWidth(14)
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sep.setStyleSheet("color:#6c7086; font-size:14px; background:transparent;")

        self._spec_axis_btns = []
        for i, label in enumerate(['Acc X', 'Acc Y', 'Acc Z']):
            btn = QToolButton()
            btn.setText(label)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setMinimumWidth(46)
            btn.setToolTip(f"Show {label} channel")
            btn.clicked.connect(lambda _, idx=i: self._select_axis(idx))
            self._spec_axis_btns.append(btn)

        nav_layout.addStretch()
        for btn in self._spec_imu_btns:
            nav_layout.addWidget(btn)
        nav_layout.addSpacing(6)
        nav_layout.addWidget(sep)
        nav_layout.addSpacing(6)
        for btn in self._spec_axis_btns:
            nav_layout.addWidget(btn)
        nav_layout.addStretch()

        pl.addWidget(self.toolbar)
        pl.addWidget(nav_bar)
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

        placeholder_axes(self.fig, "Load a .bin file and click Analyze.")
        self.canvas.draw()
        self._update_nav()

    # ─────────────────────────────────────────────────────────────────────────
    # Nav helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _update_nav(self):
        for i, btn in enumerate(self._spec_imu_btns):
            btn.setChecked(i == self._spec_imu_idx)
        for i, btn in enumerate(self._spec_axis_btns):
            btn.setChecked(i == self._spec_axis_idx)

    def _select_imu(self, idx: int):
        self._spec_imu_idx = idx
        self._update_nav()

    def _select_axis(self, idx: int):
        self._spec_axis_idx = idx
        self._update_nav()

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
            self._log(f"[Spec] Error loading file: {e}")
            return

        d     = self._data
        fname = os.path.basename(path)
        t     = d['time_s']
        self.lbl_file.setText(
            f"{fname}\n"
            f"{d['num_records']} records\n"
            f"{t[0]:.2f} – {t[-1]:.2f} s\n"
            f"Fs ≈ {d['Fs']:.1f} Hz\n"
            f"{', '.join(IMU_NAMES)}"
        )
        self.btn_analyze.setEnabled(True)
        self._log(f"[Spec] Loaded '{fname}' — {d['num_records']} records, "
                  f"Fs≈{d['Fs']:.1f} Hz")

    def _analyze(self):
        if self._data is None:
            return
        if self._worker is not None and self._worker.isRunning():
            return

        d         = self._data
        fname     = os.path.basename(self._filepath)
        imu_idx   = self._spec_imu_idx
        axis_idx  = self._spec_axis_idx
        axis_key  = ['accX_uniform', 'accY_uniform', 'accZ_uniform'][axis_idx]
        axis_lbl  = ['X', 'Y', 'Z'][axis_idx]
        acc       = d[axis_key][imu_idx]

        win      = self.spin_window.value()
        noverlap = win // 2
        nfft     = max(4096, win * 4)
        mag_lim  = self.spin_mag_lim.value()
        fmin     = self.spin_spec_fmin.value()
        fmax     = self.spin_spec_fmax.value()

        self._pending = dict(
            fname=fname, mag_lim=mag_lim, fmin=fmin, fmax=fmax,
            imu_lbl=IMU_NAMES[imu_idx], axis_lbl=axis_lbl,
        )

        self._log(f"[Spec] Analysing '{fname}' — {IMU_NAMES[imu_idx]} Acc{axis_lbl}, "
                  f"window={win}, nfft={nfft} …")
        self.lbl_status.setText("Computing…")
        self.btn_analyze.setEnabled(False)
        self.btn_load.setEnabled(False)

        placeholder_axes(self.fig, "Computing spectrogram…")
        self.canvas.draw()

        self._worker = _SpectrogramWorker(acc, d['Fs'], win, noverlap, nfft)
        self._worker.done.connect(self._on_worker_done)
        self._worker.error.connect(self._on_worker_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_worker_done(self, F, T, mag_lin):
        p        = self._pending
        fname    = p['fname']
        mag_lim  = p['mag_lim']
        fmin     = p['fmin']
        fmax     = p['fmax']
        imu_lbl  = p['imu_lbl']
        axis_lbl = p['axis_lbl']

        self.fig.clear()
        self.fig.patch.set_facecolor(plot_utils.FIG_BG)

        ax = self.fig.add_subplot(1, 1, 1)
        self._spec_ax = ax
        self._cbar    = None
        ax.set_facecolor(plot_utils.AXES_BG)

        cmap = make_whitehot_colormap()
        im   = ax.pcolormesh(T, F, mag_lin,
                             cmap=cmap, vmin=0, vmax=mag_lim,
                             shading='auto', rasterized=True)
        ax.set_ylim(fmin, fmax)

        self._cbar = self.fig.colorbar(im, ax=ax, pad=0.01)
        self._cbar.ax.tick_params(colors=plot_utils.TICK_COLOR, labelsize=8)
        self._cbar.set_label('Magnitude (m/s\u00b2)', color=plot_utils.TEXT_COLOR, fontsize=9)

        ax.set_xlabel('Flight Time (s)', color=plot_utils.TICK_COLOR, fontsize=9)
        ax.set_ylabel('Frequency (Hz)',  color=plot_utils.TICK_COLOR, fontsize=9)
        ax.set_title(
            f"Spectrogram — {imu_lbl}  Acc{axis_lbl}  |  {fname}  "
            f"(white > {mag_lim:.2f} m/s\u00b2)",
            color=plot_utils.TEXT_COLOR, fontsize=10, pad=5)
        ax.tick_params(colors=plot_utils.TICK_COLOR, labelsize=8)
        ax.grid(True, color=plot_utils.GRID_COLOR, alpha=0.4, linewidth=0.5)
        for s in ax.spines.values():
            s.set_edgecolor(plot_utils.SPINE_COLOR)

        self.fig.tight_layout(pad=1.8)
        self.canvas.draw()
        self._analyzed = True
        self._log(f"[Spec] Done — {imu_lbl} Acc{axis_lbl}  '{fname}'.")

    def _on_worker_error(self, msg: str):
        self.fig.clear()
        self.fig.patch.set_facecolor(plot_utils.FIG_BG)
        ax = self.fig.add_subplot(1, 1, 1)
        self._spec_ax = ax
        ax.set_facecolor(plot_utils.AXES_BG)
        ax.text(0.5, 0.5, f"Spectrogram error:\n{msg}",
                ha='center', va='center', color='#f38ba8',
                fontsize=10, transform=ax.transAxes)
        self.canvas.draw()
        self._log(f"[Spec] Error: {msg}")

    def _on_worker_finished(self):
        self.lbl_status.setText("")
        self.btn_analyze.setEnabled(True)
        self.btn_load.setEnabled(True)

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
            path = save_figure(self.fig, "Spectrogram")
            self._log(f"[Spec] Image saved → {path}")
        except Exception as e:
            self._log(f"[Spec] Error saving image: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Theme
    # ─────────────────────────────────────────────────────────────────────────

    def redraw_theme(self):
        """Repaint colours in-place — preserves zoom, pan, colormap scale."""
        self.fig.patch.set_facecolor(plot_utils.FIG_BG)
        self._save_img_btn.setStyleSheet(save_img_btn_style(plot_utils._dark))
        if self._spec_ax is None:
            placeholder_axes(self.fig, "Load a .bin file and click Analyze.")
            self.canvas.draw()
            return
        ax = self._spec_ax
        ax.set_facecolor(plot_utils.AXES_BG)
        ax.title.set_color(plot_utils.TEXT_COLOR)
        ax.xaxis.label.set_color(plot_utils.TICK_COLOR)
        ax.yaxis.label.set_color(plot_utils.TICK_COLOR)
        ax.tick_params(colors=plot_utils.TICK_COLOR, labelsize=8)
        ax.grid(True, color=plot_utils.GRID_COLOR, alpha=0.4, linewidth=0.5)
        for spine in ax.spines.values():
            spine.set_edgecolor(plot_utils.SPINE_COLOR)
        if self._cbar is not None:
            self._cbar.ax.tick_params(colors=plot_utils.TICK_COLOR, labelsize=8)
            self._cbar.ax.yaxis.label.set_color(plot_utils.TEXT_COLOR)
        self._update_nav()
        self.canvas.draw_idle()
