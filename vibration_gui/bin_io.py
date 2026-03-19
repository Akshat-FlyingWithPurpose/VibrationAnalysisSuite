"""
Binary file I/O for vibration .bin files.

Record format (little-endian, 18 bytes per record):
  uint32  (4 bytes) - time in milliseconds
  float32 (4 bytes) - AccX  (stored in milli-g; divided by 1000 on read → g)
  float32 (4 bytes) - AccY
  float32 (4 bytes) - AccZ
  uint16  (2 bytes) - sample rate in Hz
"""
import numpy as np

RECORD_DTYPE = np.dtype([
    ('time_ms', '<u4'),
    ('accX',    '<f4'),
    ('accY',    '<f4'),
    ('accZ',    '<f4'),
    ('rate_hz', '<u2'),
])
RECORD_SIZE = RECORD_DTYPE.itemsize  # 18 bytes


def read_bin(filepath: str) -> dict:
    """
    Read a vibration .bin file.

    Acceleration values are stored as milli-g in the file; they are divided by
    1000 on load so that all returned arrays are in units of g.

    Returns dict with:
      time_ms, time_s                     – raw timestamps
      accX, accY, accZ                    – raw (g), deduplicated
      time_uniform, accX_uniform,
        accY_uniform, accZ_uniform        – uniformly resampled (g), ready for FFT
      rate_hz, num_records, Fs
    """
    with open(filepath, 'rb') as f:
        raw = f.read()

    num_records = len(raw) // RECORD_SIZE
    if num_records == 0:
        raise ValueError(
            f"File has no complete records. "
            f"File size: {len(raw)} bytes, record size: {RECORD_SIZE} bytes."
        )

    data = np.frombuffer(raw[:num_records * RECORD_SIZE], dtype=RECORD_DTYPE)

    time_ms = data['time_ms'].astype(np.float64)
    time_s  = time_ms / 1000.0

    # Convert milli-g → g  (nan_to_num guards against corrupt float32 records)
    accX = np.nan_to_num(data['accX'].astype(np.float64) / 1000.0)
    accY = np.nan_to_num(data['accY'].astype(np.float64) / 1000.0)
    accZ = np.nan_to_num(data['accZ'].astype(np.float64) / 1000.0)

    # ── Remove duplicate timestamps (required for interpolation) ──────────
    _, unique_idx  = np.unique(time_s, return_index=True)
    time_s_unique  = time_s[unique_idx]
    accX_unique    = accX[unique_idx]
    accY_unique    = accY[unique_idx]
    accZ_unique    = accZ[unique_idx]

    # ── Uniform resampling using median dt (robust against outliers) ───────
    if len(time_s_unique) > 1:
        median_dt    = np.median(np.diff(time_s_unique))
        Fs           = 1.0 / median_dt if median_dt > 0 else float(data['rate_hz'][0])
        N_pts        = round((time_s_unique[-1] - time_s_unique[0]) / median_dt) + 1
        time_uniform = np.linspace(time_s_unique[0], time_s_unique[-1], N_pts)
        accX_uniform = np.interp(time_uniform, time_s_unique, accX_unique)
        accY_uniform = np.interp(time_uniform, time_s_unique, accY_unique)
        accZ_uniform = np.interp(time_uniform, time_s_unique, accZ_unique)
    else:
        Fs           = float(data['rate_hz'][0])
        time_uniform = time_s_unique.copy()
        accX_uniform = accX_unique.copy()
        accY_uniform = accY_unique.copy()
        accZ_uniform = accZ_unique.copy()

    return {
        'time_ms':      time_ms,
        'time_s':       time_s,
        'accX':         accX,
        'accY':         accY,
        'accZ':         accZ,
        'time_uniform': time_uniform,
        'accX_uniform': accX_uniform,
        'accY_uniform': accY_uniform,
        'accZ_uniform': accZ_uniform,
        'rate_hz':      data['rate_hz'].astype(np.float64),
        'num_records':  num_records,
        'Fs':           Fs,
    }


def write_bin(filepath: str, time_ms, accX, accY, accZ, rate_hz):
    """
    Write a vibration .bin file with the same 18-byte record format.
    accX/Y/Z must be in g units; they are multiplied by 1000 to store as milli-g.
    """
    n = len(time_ms)
    out = np.zeros(n, dtype=RECORD_DTYPE)
    out['time_ms'] = np.asarray(time_ms, dtype=np.uint32)
    out['accX']    = np.asarray(accX * 1000, dtype=np.float32)
    out['accY']    = np.asarray(accY * 1000, dtype=np.float32)
    out['accZ']    = np.asarray(accZ * 1000, dtype=np.float32)
    out['rate_hz'] = np.asarray(rate_hz, dtype=np.uint16)

    with open(filepath, 'wb') as f:
        f.write(out.tobytes())
