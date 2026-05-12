% =========================================================
%  VibeDriver_4IMU.m
%  Individual FFT figures for each arm (Beta / Alpha / Delta / Gamma)
%  Binary format: 4-byte epoch header + N x 28-byte DataPacket records
%
%  DataPacket (packed, little-endian):
%    uint32  time_us      4 bytes
%    int16   ax[4]        8 bytes   (IMU 0-3)
%    int16   ay[4]        8 bytes
%    int16   az[4]        8 bytes
%
%  IMU → Arm mapping:
%    Index 0  →  Beta Arm   (MUX ch 7, 0x69)
%    Index 1  →  Alpha Arm  (MUX ch 4, 0x69)
%    Index 2  →  Delta Arm  (MUX ch 3, 0x69)
%    Index 3  →  Gamma Arm  (MUX ch 1, 0x68)
% =========================================================

clear; clc; close all;

% ── Constants ──────────────────────────────────────────────────────────────
ACCEL_SCALE  = 8192.0;   % LSB per g  (ICM-20948, ±4 g)
G_TO_MS2     = 9.80665;  % m/s²  per  g
RECORD_SIZE  = 28;       % bytes per DataPacket
HEADER_SIZE  = 4;        % bytes — uint32 startEpoch
NUM_IMUS     = 4;
SMOOTH_WIN   = 10;       % moving-average window for FFT smoothing
FREQ_MIN     = 0;        % Hz — plot x-axis lower bound
FREQ_MAX     = 50;       % Hz — plot x-axis upper bound

IMU_NAMES    = {'Beta Arm', 'Alpha Arm', 'Delta Arm', 'Gamma Arm'};
AXIS_LABELS  = {'AccX', 'AccY', 'AccZ'};
AXIS_COLORS  = {'#1565c0', '#d32f2f', '#2e7d32'};   % blue / red / green

% ── Locate .bin file ───────────────────────────────────────────────────────
script_dir = fileparts(mfilename('fullpath'));
bin_files  = dir(fullfile(script_dir, '*.bin'));

if isempty(bin_files)
    error('No .bin files found in the script directory:\n  %s', script_dir);
elseif numel(bin_files) == 1
    fullpath = fullfile(script_dir, bin_files(1).name);
    fprintf('Auto-loading: %s\n', bin_files(1).name);
else
    fprintf('\nMultiple .bin files found:\n');
    for k = 1:numel(bin_files)
        fprintf('  [%d]  %s\n', k, bin_files(k).name);
    end
    idx = input('Select file number: ');
    if isempty(idx) || idx < 1 || idx > numel(bin_files)
        error('Invalid selection.');
    end
    fullpath = fullfile(script_dir, bin_files(idx).name);
    fprintf('Loading: %s\n', bin_files(idx).name);
end

% ── Read binary file ────────────────────────────────────────────────────────
fid = fopen(fullpath, 'rb');
if fid == -1
    error('Cannot open file: %s', fullpath);
end
raw = fread(fid, Inf, 'uint8=>uint8');
fclose(fid);

if numel(raw) < HEADER_SIZE + RECORD_SIZE
    error('File too small — no complete records.');
end

% Skip 4-byte epoch header
start_epoch  = double(typecast(raw(1:4), 'uint32'));
payload      = raw(HEADER_SIZE+1 : end);
num_records  = floor(numel(payload) / RECORD_SIZE);
fprintf('Records found: %d\n', num_records);

payload = payload(1 : num_records * RECORD_SIZE);
payload = reshape(payload, RECORD_SIZE, num_records);   % 28 x N

% ── Parse fields ──────────────────────────────────────────────────────────
% Bytes 1-4   : uint32 time_us
% Bytes 5-12  : int16 ax[4]   (one per IMU, interleaved)
% Bytes 13-20 : int16 ay[4]
% Bytes 21-28 : int16 az[4]

time_us = double(typecast(reshape(payload(1:4,  :), 1, []), 'uint32'))';
time_s  = time_us / 1e6;

% Raw int16 for each axis, shape  N x 4
ax_raw = reshape(double(typecast(reshape(payload(5:12,  :), 1, []), 'int16')), 4, num_records)';
ay_raw = reshape(double(typecast(reshape(payload(13:20, :), 1, []), 'int16')), 4, num_records)';
az_raw = reshape(double(typecast(reshape(payload(21:28, :), 1, []), 'int16')), 4, num_records)';

% Convert LSB → m/s²
ax_ms2 = ax_raw / ACCEL_SCALE * G_TO_MS2;
ay_ms2 = ay_raw / ACCEL_SCALE * G_TO_MS2;
az_ms2 = az_raw / ACCEL_SCALE * G_TO_MS2;

fprintf('Duration: %.3f – %.3f s  (%.3f s)\n', time_s(1), time_s(end), time_s(end)-time_s(1));

% ── Uniform resampling (same approach as Python app) ──────────────────────
[time_s_unique, unique_idx] = unique(time_s);

median_dt    = median(diff(time_s_unique));
Fs           = 1.0 / median_dt;
N_pts        = round((time_s_unique(end) - time_s_unique(1)) / median_dt) + 1;
time_uniform = linspace(time_s_unique(1), time_s_unique(end), N_pts);

fprintf('Fs (uniform): %.2f Hz\n\n', Fs);

ax_u = zeros(N_pts, NUM_IMUS);
ay_u = zeros(N_pts, NUM_IMUS);
az_u = zeros(N_pts, NUM_IMUS);

for i = 1:NUM_IMUS
    ax_u(:,i) = interp1(time_s_unique, ax_ms2(unique_idx, i), time_uniform, 'linear');
    ay_u(:,i) = interp1(time_s_unique, ay_ms2(unique_idx, i), time_uniform, 'linear');
    az_u(:,i) = interp1(time_s_unique, az_ms2(unique_idx, i), time_uniform, 'linear');
end

% ── FFT helper ─────────────────────────────────────────────────────────────
function [f_vec, sm] = compute_fft(sig, Fs, win)
    sig = detrend(sig);           % remove DC + linear drift
    N   = length(sig);
    f_vec = Fs * (0:floor(N/2)) / N;
    X   = fft(sig);
    mag = abs(X / N);
    mag = mag(1:floor(N/2)+1);
    mag(2:end-1) = 2 * mag(2:end-1);
    if mod(N,2) == 1, mag(end) = 2*mag(end); end
    sm  = movmean(mag, win);
end

% ── Per-IMU figures ─────────────────────────────────────────────────────────
[~, fname_base, ~] = fileparts(fullpath);

for imu = 1:NUM_IMUS
    arm_name = IMU_NAMES{imu};
    fprintf('Plotting %s ...\n', arm_name);

    % Collect signals for this IMU
    sigs = {ax_u(:,imu), ay_u(:,imu), az_u(:,imu)};

    fig = figure('Name', sprintf('%s — %s', arm_name, fname_base), ...
                 'NumberTitle', 'off', ...
                 'Units', 'normalized', ...
                 'Position', [0.05 + (imu-1)*0.05, 0.1, 0.55, 0.75]);

    for ax_idx = 1:3
        sig = sigs{ax_idx};
        [f_vec, sm] = compute_fft(sig, Fs, SMOOTH_WIN);

        % Limit to requested frequency range
        freq_mask = (f_vec >= FREQ_MIN) & (f_vec <= FREQ_MAX);

        subplot(3, 1, ax_idx);
        plot(f_vec(freq_mask), sm(freq_mask), ...
             'Color', AXIS_COLORS{ax_idx}, 'LineWidth', 1.2);
        grid on;
        xlim([FREQ_MIN, FREQ_MAX]);
        xlabel('Frequency (Hz)', 'FontSize', 9);
        ylabel('|FFT| (m/s²)',   'FontSize', 9);
        title(sprintf('%s — %s', arm_name, AXIS_LABELS{ax_idx}), ...
              'FontSize', 10, 'FontWeight', 'bold');

        % Annotate dominant peak
        [peak_val, peak_idx] = max(sm(freq_mask));
        f_clipped = f_vec(freq_mask);
        peak_freq = f_clipped(peak_idx);
        text(peak_freq, peak_val, ...
             sprintf('  %.2f Hz\n  %.4f m/s²', peak_freq, peak_val), ...
             'FontSize', 7, 'Color', AXIS_COLORS{ax_idx}, ...
             'VerticalAlignment', 'bottom');
    end

    sgtitle(sprintf('FFT — %s  |  %s  (Fs = %.1f Hz)', ...
            arm_name, fname_base, Fs), ...
            'FontSize', 11, 'FontWeight', 'bold');
end

fprintf('\nDone. %d figures generated.\n', NUM_IMUS);
