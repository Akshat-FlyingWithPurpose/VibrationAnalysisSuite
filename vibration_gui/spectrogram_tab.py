"""
Spectrogram Tab — high-resolution white-hot spectrogram for a single .bin file.
Shows one axis at a time (AccX / AccY / AccZ) with prev/next navigation.
"""
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QDoubleSpinBox, QSpinBox,
    QSplitter, QFileDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from .bin_io import read_bin
from .analysis import compute_spectrogram, make_whitehot_colormap
from . import plot_utils
from .plot_utils import make_canvas, placeholder_axes


# ─────────────────────────────────────────────────────────────────────────────
# Background worker — keeps the GUI responsive during heavy computation
# ─────────────────────────────────────────────────────────────────────────────

class _SpectrogramWorker(QThread):
    done  = pyqtSignal(object, object, object, object, object)  # F, T, magX, magY, magZ
    error = pyqtSignal(str)

    def __init__(self, accX, accY, accZ, Fs, window, noverlap, nfft):
        super().__init__()
        self._accX     = accX
        self._accY     = accY
        self._accZ     = accZ
        self._Fs       = Fs
        self._window   = window
        self._noverlap = noverlap
        self._nfft     = nfft

    def run(self):
        try:
            F,  T,  magX = compute_spectrogram(
                self._accX, self._Fs,
                window=self._window, noverlap=self._noverlap, nfft=self._nfft)
            _F, _T, magY = compute_spectrogram(
                self._accY, self._Fs,
                window=self._window, noverlap=self._noverlap, nfft=self._nfft)
            _F, _T, magZ = compute_spectrogram(
                self._accZ, self._Fs,
                window=self._window, noverlap=self._noverlap, nfft=self._nfft)
            self.done.emit(F, T, magX, magY, magZ)
        except Exception as e:
            self.error.emit(str(e))


class SpectrogramTab(QWidget):
    _AXIS_LABELS = ['AccX', 'AccY', 'AccZ']

    def __init__(self, log_fn):
        super().__init__()
        self._log      = log_fn
        self._data     = None
        self._filepath = None
        self._analyzed = False
        self._worker   = None
        self._pending  = {}

        # Stored spectrogram data for all three axes
        self._spec_data = None   # dict with F, T, mags list, fname, mag_lim, fmin, fmax
        self._cur_axis  = 0      # 0=X, 1=Y, 2=Z

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

        cl.addWidget(fg)

        # Spectrogram settings group
        spg = QGroupBox("Spectrogram")
        spl = QVBoxLayout(spg)

        spl.addWidget(QLabel("Window Size:"))
        self.spin_window = QSpinBox()
        self.spin_window.setRange(64, 16384)
        self.spin_window.setValue(1024)
        self.spin_window.setSingleStep(256)
        spl.addWidget(self.spin_window)

        spl.addWidget(QLabel("Magnitude Limit (g):"))
        self.spin_mag_lim = QDoubleSpinBox()
        self.spin_mag_lim.setRange(0.0001, 100000.0)
        self.spin_mag_lim.setValue(1.2)
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

        # Analyze button
        self.btn_analyze = QPushButton("Analyze")
        self.btn_analyze.setObjectName("btn_spec")
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.clicked.connect(self._analyze)
        cl.addWidget(self.btn_analyze)

        # Status label (shown while computing)
        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("info")
        self.lbl_status.setWordWrap(True)
        cl.addWidget(self.lbl_status)

        cl.addStretch()
        splitter.addWidget(ctrl)

        # ── Right: plot + navigation ─────────────────────────────────────────
        plot_w = QWidget()
        pl = QVBoxLayout(plot_w)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(0)

        self.fig, self.canvas, self.toolbar = make_canvas(plot_w)
        pl.addWidget(self.toolbar)
        pl.addWidget(self.canvas)

        # Navigation bar: ◀  Acc X (1/3)  ▶
        nav_bar = QWidget()
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(8, 4, 8, 4)
        nav_layout.setSpacing(12)

        self.btn_prev = QPushButton("◀  Prev")
        self.btn_prev.setFixedWidth(90)
        self.btn_prev.setEnabled(False)
        self.btn_prev.clicked.connect(self._show_prev)

        self.lbl_axis = QLabel("")
        self.lbl_axis.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_next = QPushButton("Next  ▶")
        self.btn_next.setFixedWidth(90)
        self.btn_next.setEnabled(False)
        self.btn_next.clicked.connect(self._show_next)

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addStretch()
        nav_layout.addWidget(self.lbl_axis)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)

        pl.addWidget(nav_bar)

        splitter.addWidget(plot_w)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        placeholder_axes(self.fig, "Load a .bin file and click Analyze.")
        self.canvas.draw()

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
            f"Fs ≈ {d['Fs']:.1f} Hz"
        )
        self.btn_analyze.setEnabled(True)
        self._log(f"[Spec] Loaded '{fname}' — {d['num_records']} records, "
                  f"Fs≈{d['Fs']:.1f} Hz")

    def _analyze(self):
        if self._data is None:
            return
        if self._worker is not None and self._worker.isRunning():
            return

        d        = self._data
        fname    = os.path.basename(self._filepath)
        win      = self.spin_window.value()
        noverlap = win // 2
        nfft     = max(4096, win * 4)
        mag_lim  = self.spin_mag_lim.value()
        fmin     = self.spin_spec_fmin.value()
        fmax     = self.spin_spec_fmax.value()

        self._pending = dict(fname=fname, mag_lim=mag_lim, fmin=fmin, fmax=fmax)

        self._log(f"[Spec] Analysing '{fname}' — window={win}, nfft={nfft} …")
        self.lbl_status.setText("Computing…")
        self.btn_analyze.setEnabled(False)
        self.btn_load.setEnabled(False)

        placeholder_axes(self.fig, "Computing spectrogram…")
        self.canvas.draw()

        self._worker = _SpectrogramWorker(
            d['accX_uniform'], d['accY_uniform'], d['accZ_uniform'],
            d['Fs'], win, noverlap, nfft)
        self._worker.done.connect(self._on_worker_done)
        self._worker.error.connect(self._on_worker_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_worker_done(self, F, T, magX, magY, magZ):
        p = self._pending
        self._spec_data = dict(
            F=F, T=T,
            mags=[magX, magY, magZ],
            fname=p['fname'],
            mag_lim=p['mag_lim'],
            fmin=p['fmin'],
            fmax=p['fmax'],
        )
        self._cur_axis = 0
        self._draw_current()
        self._analyzed = True
        self._log(f"[Spec] Done — '{p['fname']}'.")

    def _on_worker_error(self, msg: str):
        self.fig.clear()
        self.fig.patch.set_facecolor(plot_utils.FIG_BG)
        ax = self.fig.add_subplot(1, 1, 1)
        ax.set_facecolor(plot_utils.AXES_BG)
        ax.text(0.5, 0.5, f"Spectrogram error:\n{msg}",
                ha='center', va='center', color='#f38ba8',
                fontsize=10, transform=ax.transAxes)
        self.canvas.draw()
        self._log(f"[Spec] Spectrogram error: {msg}")

    def _on_worker_finished(self):
        self.lbl_status.setText("")
        self.btn_analyze.setEnabled(True)
        self.btn_load.setEnabled(True)

    # ─────────────────────────────────────────────────────────────────────────
    # Navigation
    # ─────────────────────────────────────────────────────────────────────────

    def _show_prev(self):
        if self._spec_data is None:
            return
        self._cur_axis = (self._cur_axis - 1) % 3
        self._draw_current()

    def _show_next(self):
        if self._spec_data is None:
            return
        self._cur_axis = (self._cur_axis + 1) % 3
        self._draw_current()

    def _draw_current(self):
        d       = self._spec_data
        idx     = self._cur_axis
        label   = self._AXIS_LABELS[idx]
        mag     = d['mags'][idx]

        self.fig.clear()
        self.fig.patch.set_facecolor(plot_utils.FIG_BG)

        ax = self.fig.add_subplot(1, 1, 1)
        ax.set_facecolor(plot_utils.AXES_BG)

        cmap = make_whitehot_colormap()
        im   = ax.pcolormesh(d['T'], d['F'], mag,
                             cmap=cmap, vmin=0, vmax=d['mag_lim'],
                             shading='auto', rasterized=True)
        ax.set_ylim(d['fmin'], d['fmax'])

        cbar = self.fig.colorbar(im, ax=ax, pad=0.01)
        cbar.ax.tick_params(colors=plot_utils.TICK_COLOR, labelsize=8)
        cbar.set_label('Magnitude (g)', color=plot_utils.TEXT_COLOR, fontsize=9)

        ax.set_xlabel('Flight Time (s)', color=plot_utils.TICK_COLOR, fontsize=9)
        ax.set_ylabel('Frequency (Hz)', color=plot_utils.TICK_COLOR, fontsize=9)
        ax.set_title(
            f"Spectrogram — {label}  |  {d['fname']}  (white > {d['mag_lim']:.4f} g)",
            color=plot_utils.TEXT_COLOR, fontsize=10, pad=5)
        ax.tick_params(colors=plot_utils.TICK_COLOR, labelsize=8)
        ax.grid(True, color=plot_utils.GRID_COLOR, alpha=0.4, linewidth=0.5)
        for s in ax.spines.values():
            s.set_edgecolor(plot_utils.SPINE_COLOR)

        self.fig.tight_layout(pad=1.8)
        self.canvas.draw()

        # Update nav bar
        self.lbl_axis.setText(f"{label}  ({idx + 1} / 3)")
        self.btn_prev.setEnabled(True)
        self.btn_next.setEnabled(True)

    # ─────────────────────────────────────────────────────────────────────────
    # Theme
    # ─────────────────────────────────────────────────────────────────────────

    def redraw_theme(self):
        """Repaint colours in-place — re-draws the current axis with new theme."""
        if self._spec_data is None:
            self.fig.patch.set_facecolor(plot_utils.FIG_BG)
            placeholder_axes(self.fig, "Load a .bin file and click Analyze.")
            self.canvas.draw()
            return
        self._draw_current()
