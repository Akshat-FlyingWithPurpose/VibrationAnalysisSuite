"""
Binary file I/O for vibration .bin files — 4-IMU format.

File structure:
  Header : 4 bytes  — uint32 startEpoch (Unix timestamp, little-endian)
  Records: N × 28 bytes — DataPacket (packed, little-endian)

DataPacket layout:
  uint32   time_us      4 bytes  microseconds (Teensy micros())
  int16_t  ax[4]        8 bytes  AccX for IMU 0-3  (raw LSB)
  int16_t  ay[4]        8 bytes  AccY for IMU 0-3
  int16_t  az[4]        8 bytes  AccZ for IMU 0-3

IMU full-scale: ±4 g  →  sensitivity = 8192 LSB/g
"""
import numpy as np

NUM_IMUS    = 4
IMU_NAMES   = ['Beta Arm', 'Alpha Arm', 'Delta Arm', 'Gamma Arm']
ACCEL_SCALE = 8192.0   # LSB per g  (ICM-20948, ±4 g)
G_TO_MS2    = 9.80665  # standard gravity: converts g → m/s²
HEADER_SIZE = 4        # bytes — startEpoch uint32 at start of file

RECORD_DTYPE = np.dtype([
    ('time_us', '<u4'),
    ('ax',      '<i2', NUM_IMUS),
    ('ay',      '<i2', NUM_IMUS),
    ('az',      '<i2', NUM_IMUS),
])
RECORD_SIZE = RECORD_DTYPE.itemsize   # 28 bytes


def read_bin(filepath: str) -> dict:
    """
    Read a 4-IMU vibration .bin file.

    Returns dict with:
      time_us, time_s          – raw timestamps (arrays, length = num_records)
      time_uniform             – single uniform time grid (seconds)
      accX, accY, accZ         – list of 4 arrays each, raw + deduplicated  [g]
      accX_uniform,
        accY_uniform,
        accZ_uniform           – list of 4 arrays each, uniformly resampled [g]
      Fs                       – sample rate (Hz)
      num_records              – number of records
      start_epoch              – Unix timestamp from file header
    """
    with open(filepath, 'rb') as f:
        raw = f.read()

    if len(raw) < HEADER_SIZE:
        raise ValueError("File too small — missing 4-byte epoch header.")

    start_epoch = int.from_bytes(raw[:HEADER_SIZE], 'little')
    payload     = raw[HEADER_SIZE:]

    num_records = len(payload) // RECORD_SIZE
    if num_records == 0:
        raise ValueError(
            f"File has no complete records.  "
            f"Payload: {len(payload)} bytes, record size: {RECORD_SIZE} bytes."
        )

    data = np.frombuffer(payload[:num_records * RECORD_SIZE], dtype=RECORD_DTYPE)

    time_us = data['time_us'].astype(np.float64)
    time_s  = time_us / 1_000_000.0

    # Raw acc per IMU: convert LSB → m/s², replace NaN/Inf from corrupt records
    accX = [np.nan_to_num(data['ax'][:, i].astype(np.float64) / ACCEL_SCALE * G_TO_MS2)
            for i in range(NUM_IMUS)]
    accY = [np.nan_to_num(data['ay'][:, i].astype(np.float64) / ACCEL_SCALE * G_TO_MS2)
            for i in range(NUM_IMUS)]
    accZ = [np.nan_to_num(data['az'][:, i].astype(np.float64) / ACCEL_SCALE * G_TO_MS2)
            for i in range(NUM_IMUS)]

    # Deduplicate timestamps (shared across all IMUs in each packet)
    _, unique_idx = np.unique(time_s, return_index=True)
    time_s_u = time_s[unique_idx]

    # Uniform resampling using median Δt (robust against jitter)
    if len(time_s_u) > 1:
        median_dt    = np.median(np.diff(time_s_u))
        Fs           = 1.0 / median_dt if median_dt > 0 else 1000.0
        N_pts        = round((time_s_u[-1] - time_s_u[0]) / median_dt) + 1
        time_uniform = np.linspace(time_s_u[0], time_s_u[-1], N_pts)
    else:
        Fs           = 1000.0
        time_uniform = time_s_u.copy()

    accX_uniform = [np.interp(time_uniform, time_s_u, accX[i][unique_idx])
                    for i in range(NUM_IMUS)]
    accY_uniform = [np.interp(time_uniform, time_s_u, accY[i][unique_idx])
                    for i in range(NUM_IMUS)]
    accZ_uniform = [np.interp(time_uniform, time_s_u, accZ[i][unique_idx])
                    for i in range(NUM_IMUS)]

    return {
        'time_us':      time_us,
        'time_s':       time_s,
        'time_uniform': time_uniform,
        'accX':         accX,           # list of 4 arrays [m/s²]
        'accY':         accY,
        'accZ':         accZ,
        'accX_uniform': accX_uniform,   # list of 4 arrays [m/s²], uniform
        'accY_uniform': accY_uniform,
        'accZ_uniform': accZ_uniform,
        'Fs':           Fs,
        'num_records':  num_records,
        'start_epoch':  start_epoch,
    }


def write_bin(filepath: str, time_us, accX_list, accY_list, accZ_list,
              start_epoch: int = 0):
    """
    Write a 4-IMU vibration .bin file in the same packed format.

    Parameters
    ----------
    time_us      : array-like, uint32 microsecond timestamps
    accX_list    : list of 4 arrays in m/s²  (converted → g → int16)
    accY_list    : list of 4 arrays in m/s²
    accZ_list    : list of 4 arrays in m/s²
    start_epoch  : uint32 Unix timestamp for the file header
    """
    n   = len(time_us)
    out = np.zeros(n, dtype=RECORD_DTYPE)
    out['time_us'] = np.asarray(time_us, dtype=np.uint32)
    for i in range(NUM_IMUS):
        out['ax'][:, i] = np.clip(
            np.round(accX_list[i] / G_TO_MS2 * ACCEL_SCALE), -32768, 32767).astype(np.int16)
        out['ay'][:, i] = np.clip(
            np.round(accY_list[i] / G_TO_MS2 * ACCEL_SCALE), -32768, 32767).astype(np.int16)
        out['az'][:, i] = np.clip(
            np.round(accZ_list[i] / G_TO_MS2 * ACCEL_SCALE), -32768, 32767).astype(np.int16)

    with open(filepath, 'wb') as f:
        f.write(int(start_epoch).to_bytes(4, 'little'))
        f.write(out.tobytes())
