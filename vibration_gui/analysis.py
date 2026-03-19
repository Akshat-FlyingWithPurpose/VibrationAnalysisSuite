"""
Signal processing for vibration analysis.
Matches MATLAB normalisation used in RawCrop.m, VibeDriver.m, Spectrogram_SFFT.m.
"""
import numpy as np
from scipy import signal as sp_signal
from scipy.signal import detrend
import matplotlib.cm as cm
from matplotlib.colors import LinearSegmentedColormap


# ─────────────────────────────────────────────────────────────────────────────
# FFT
# ─────────────────────────────────────────────────────────────────────────────

def compute_fft(data: np.ndarray, Fs: float, smooth_win: int = 10):
    """
    Single-sided FFT magnitude spectrum — MATLAB-compatible normalisation.

    Returns
    -------
    f          : frequency vector (Hz)
    mag        : raw magnitude
    smooth_mag : moving-average smoothed magnitude
    """
    clean = detrend(data)   # remove DC offset and linear drift (matches MATLAB detrend)
    N = len(clean)
    X = np.fft.fft(clean)
    f = Fs * np.arange(N // 2 + 1) / N

    mag = np.abs(X / N)[: N // 2 + 1].copy()
    mag[1:-1] *= 2  # single-sided: double non-DC / non-Nyquist bins

    # Moving-average smoothing (mirrors MATLAB movmean)
    kernel     = np.ones(smooth_win) / smooth_win
    smooth_mag = np.convolve(mag, kernel, mode='same')

    return f, mag, smooth_mag


# ─────────────────────────────────────────────────────────────────────────────
# Segmented FFT  (Spectrogram_SFFT.m — Figure 1)
# ─────────────────────────────────────────────────────────────────────────────

def compute_segmented_fft(data: np.ndarray, Fs: float,
                           num_segments: int = 10, smooth_win: int = 10):
    """
    Split data into equal-length segments and compute FFT for each.

    Returns list of dicts:
        idx, f, smooth_mag, t_start, t_end
    """
    samples_per_seg = len(data) // num_segments
    segments = []
    for s in range(num_segments):
        i0  = s * samples_per_seg
        i1  = i0 + samples_per_seg
        seg = data[i0:i1]
        f, _, smooth_mag = compute_fft(seg, Fs, smooth_win)
        segments.append({
            'idx':       s + 1,
            'f':         f,
            'smooth_mag': smooth_mag,
            't_start':   i0 / Fs,
            't_end':     i1 / Fs,
        })
    return segments


# ─────────────────────────────────────────────────────────────────────────────
# Spectrogram  (Spectrogram_SFFT.m — Figure 2)
# ─────────────────────────────────────────────────────────────────────────────

def compute_spectrogram(data: np.ndarray, Fs: float,
                         window: int = 1024, noverlap: int = 512,
                         nfft: int = 4096):
    """
    Compute spectrogram; return linear magnitude sqrt(PSD).
    Matches MATLAB: [S,F,T,P] = spectrogram(accX, window, noverlap, nfft, Fs, 'yaxis')
                    Mag_Linear = sqrt(P)

    Returns
    -------
    F           : frequency vector (Hz)
    T           : time vector (s)
    mag_linear  : sqrt(PSD)  shape = (len(F), len(T))
    """
    noverlap = min(noverlap, window - 1)
    f, t, Pxx = sp_signal.spectrogram(
        data, fs=Fs,
        window=sp_signal.get_window('hann', window),
        nperseg=window,
        noverlap=noverlap,
        nfft=nfft,
        scaling='density',
    )
    return f, t, np.sqrt(Pxx)


# ─────────────────────────────────────────────────────────────────────────────
# Colourmap — "White-Hot" (Spectrogram_SFFT.m custom_map)
# ─────────────────────────────────────────────────────────────────────────────

def make_whitehot_colormap():
    """
    Reproduce the MATLAB white-hot colourmap from Spectrogram_SFFT.m.

    Control points (value in 0–300 range → normalised to 0–1):
        0   → (0,     0,    0.1)  dark navy
        100 → (0,     0.15, 0.5)  medium blue
        140 → (1,     0.2,  0)    orange-red
        180 → (1,     0,    0)    red
        210 → (1,     0,    0.5)  red-pink
        300 → (1,     1,    1)    white
    """
    control = [
        (0   / 300, (0.0,  0.00, 0.10)),
        (100 / 300, (0.0,  0.15, 0.50)),
        (140 / 300, (1.0,  0.20, 0.00)),
        (180 / 300, (1.0,  0.00, 0.00)),
        (210 / 300, (1.0,  0.00, 0.50)),
        (300 / 300, (1.0,  1.00, 1.00)),
    ]
    return LinearSegmentedColormap.from_list(
        'whitehot',
        [(pos, rgb) for pos, rgb in control],
        N=256,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def jet_colors(n: int):
    """Return n evenly-spaced colours from the jet colourmap."""
    cmap = cm.get_cmap('jet')
    return [cmap(i / max(n - 1, 1)) for i in range(n)]


def distinct_colors(n: int):
    """Return n visually-distinct colours for multi-file overlays."""
    palette = [
        '#89b4fa', '#f38ba8', '#a6e3a1', '#fab387',
        '#cba6f7', '#89dceb', '#f9e2af', '#94e2d5',
        '#eba0ac', '#b4befe',
    ]
    return [palette[i % len(palette)] for i in range(n)]
