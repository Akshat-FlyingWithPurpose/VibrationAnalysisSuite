

% --- Select multiple BIN files
[filenames, path] = uigetfile('*.bin', 'Select BIN files', 'MultiSelect', 'on');
if isequal(filenames, 0)
    disp('No files selected. Exiting.');
    return;
end
if ischar(filenames)
    filenames = {filenames};
end
numFiles = length(filenames);

% --- Colors for plotting
colors = lines(numFiles);

% --- Initialize figures
figFFT_X = figure; hold on; title('Smoothed FFT - AccX');
xlabel('Frequency (Hz)'); ylabel('|FFT X|'); grid on;

figFFT_Y = figure; hold on; title('Smoothed FFT - AccY');
xlabel('Frequency (Hz)'); ylabel('|FFT Y|'); grid on;

figFFT_Z = figure; hold on; title('Smoothed FFT - AccZ');
xlabel('Frequency (Hz)'); ylabel('|FFT Z|'); grid on;

% figPSD_X = figure; hold on; title('PSD - AccX');
% xlabel('Frequency (Hz)'); ylabel('Power/Frequency (dB/Hz)'); grid on;
%
% figPSD_Y = figure; hold on; title('PSD - AccY');
% xlabel('Frequency (Hz)'); ylabel('Power/Frequency (dB/Hz)'); grid on;
%
% figPSD_Z = figure; hold on; title('PSD - AccZ');
% xlabel('Frequency (Hz)'); ylabel('Power/Frequency (dB/Hz)'); grid on;

% figPhase_X = figure; hold on; title('Phase Spectrum - AccX');
% xlabel('Frequency (Hz)'); ylabel('Phase (radians)'); grid on;
%
% figPhase_Y = figure; hold on; title('Phase Spectrum - AccY');
% xlabel('Frequency (Hz)'); ylabel('Phase (radians)'); grid on;
%
% figPhase_Z = figure; hold on; title('Phase Spectrum - AccZ');
% xlabel('Frequency (Hz)'); ylabel('Phase (radians)'); grid on;

figTime_X = figure; hold on; title('Time-domain - AccX');
xlabel('Time (s)'); ylabel('Acceleration (m/s^2)'); grid on;

figTime_Y = figure; hold on; title('Time-domain - AccY');
xlabel('Time (s)'); ylabel('Acceleration (m/s^2)'); grid on;

figTime_Z = figure; hold on; title('Time-domain - AccZ');
xlabel('Time (s)'); ylabel('Acceleration (m/s^2)'); grid on;

% --- Loop through each file
for k = 1:numFiles
    filename = filenames{k};
    fullpath = fullfile(path, filename);
    fprintf('Processing %s...\n', filename);

    % ---------------------------------------------------------------
    % BIN to Data Conversion
    % Format (little-endian): uint32 | float32 | float32 | float32 | uint16
    % Bytes per record:          4   +    4    +    4    +    4    +   2  = 18
    % ---------------------------------------------------------------
    RECORD_SIZE = 18;

    fid = fopen(fullpath, 'rb');
    if fid == -1
        warning('Could not open file: %s', fullpath);
        continue;
    end
    raw = fread(fid, Inf, 'uint8=>uint8');
    fclose(fid);

    num_records = floor(length(raw) / RECORD_SIZE);
    if num_records == 0
        warning('File %s has no complete records.', filename);
        continue;
    end

    raw = raw(1 : num_records * RECORD_SIZE);
    raw = reshape(raw, RECORD_SIZE, num_records);  % 18 x N matrix

    % Reinterpret bytes for each field (little-endian on all platforms)
    time_ms = double(typecast(reshape(raw(1:4,  :), 1, []), 'uint32'))';
    accX    = double(typecast(reshape(raw(5:8,  :), 1, []), 'single'))';
    accY    = double(typecast(reshape(raw(9:12, :), 1, []), 'single'))';
    accZ    = double(typecast(reshape(raw(13:16,:), 1, []), 'single'))';
    % rate_hz = double(typecast(reshape(raw(17:18,:), 1, []), 'uint16'))'; % available if needed

    fprintf('  > Read %d records.\n', num_records);

    % ---------------------------------------------------------------
    % Analysisa
    % ---------------------------------------------------------------
    time_s = time_ms / 1000;
    dt = mean(diff(time_s));
    Fs = 1 / dt;
    N = length(accX);
    fprintf('  > Detected Fs: %.2f Hz\n', Fs);

    % Frequency vector
    f = Fs * (0:(N/2)) / N;

    % FFT
    X = fft(accX);
    Y = fft(accY);
    Z = fft(accZ);

    % Single-sided magnitude spectrum (MATLAB style)
    magX = abs(X / N); magX = magX(1:N/2+1); magX(2:end-1) = 2 * magX(2:end-1);
    magY = abs(Y / N); magY = magY(1:N/2+1); magY(2:end-1) = 2 * magY(2:end-1);
    magZ = abs(Z / N); magZ = magZ(1:N/2+1); magZ(2:end-1) = 2 * magZ(2:end-1);

    % Smoothing
    win = 10;
    smoothMagX = movmean(magX, win);
    smoothMagY = movmean(magY, win);
    smoothMagZ = movmean(magZ, win);

    % % PSD
    % psdX = (1/(Fs*N)) * abs(X).^2; psdX = psdX(1:N/2+1); psdX(2:end-1) = 2*psdX(2:end-1);
    % psdY = (1/(Fs*N)) * abs(Y).^2; psdY = psdY(1:N/2+1); psdY(2:end-1) = 2*psdY(2:end-1);
    % psdZ = (1/(Fs*N)) * abs(Z).^2; psdZ = psdZ(1:N/2+1); psdZ(2:end-1) = 2*psdZ(2:end-1);

    % % Phase
    % phaseX = unwrap(angle(X(1:N/2+1)));
    % phaseY = unwrap(angle(Y(1:N/2+1)));
    % phaseZ = unwrap(angle(Z(1:N/2+1)));

    % Plot FFT
    figure(figFFT_X); plot(f, smoothMagX, 'Color', colors(k,:), 'DisplayName', filename);
    figure(figFFT_Y); plot(f, smoothMagY, 'Color', colors(k,:), 'DisplayName', filename);
    figure(figFFT_Z); plot(f, smoothMagZ, 'Color', colors(k,:), 'DisplayName', filename);

    % % Plot PSD
    % figure(figPSD_X); plot(f, 10*log10(psdX), 'Color', colors(k,:), 'DisplayName', filename);
    % figure(figPSD_Y); plot(f, 10*log10(psdY), 'Color', colors(k,:), 'DisplayName', filename);
    % figure(figPSD_Z); plot(f, 10*log10(psdZ), 'Color', colors(k,:), 'DisplayName', filename);

    % % Plot Phase
    % figure(figPhase_X); plot(f, phaseX, 'Color', colors(k,:), 'DisplayName', filename);
    % figure(figPhase_Y); plot(f, phaseY, 'Color', colors(k,:), 'DisplayName', filename);
    % figure(figPhase_Z); plot(f, phaseZ, 'Color', colors(k,:), 'DisplayName', filename);

    % Plot Time Domain
    figure(figTime_X); plot(time_s, accX, 'Color', colors(k,:), 'DisplayName', filename);
    figure(figTime_Y); plot(time_s, accY, 'Color', colors(k,:), 'DisplayName', filename);
    figure(figTime_Z); plot(time_s, accZ, 'Color', colors(k,:), 'DisplayName', filename);
end

% --- Add legends and set limits
figure(figFFT_X); ylim([0 170]); legend show;
figure(figFFT_Y); ylim([0 170]); legend show;
figure(figFFT_Z); ylim([0 170]); legend show;
% figure(figPSD_X); legend show;
% figure(figPSD_Y); legend show;
% figure(figPSD_Z); legend show;
% figure(figPhase_X); legend show;
% figure(figPhase_Y); legend show;
% figure(figPhase_Z); legend show;
figure(figTime_X); legend show;
figure(figTime_Y); legend show;
figure(figTime_Z); legend show;
