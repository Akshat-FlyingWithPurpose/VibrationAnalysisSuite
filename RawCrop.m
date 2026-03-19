% --- BIN File Cropper ---
% Load a single BIN file, view time-domain data, crop by time range,
% and export the cropped data as a new BIN file compatible with FFT_Analyzer.m

close all;

% --- Load BIN file
[filename, path] = uigetfile('*.bin', 'Select a BIN file to crop');
if isequal(filename, 0)
    disp('No file selected. Exiting.');
    return;
end
fullpath = fullfile(path, filename);
fprintf('Loading %s...\n', filename);

% --- Read BIN file
% Format (little-endian): uint32 | float32 | float32 | float32 | uint16 = 18 bytes
RECORD_SIZE = 18;

fid = fopen(fullpath, 'rb');
if fid == -1
    error('Could not open file: %s', fullpath);
end
raw = fread(fid, Inf, 'uint8=>uint8');
fclose(fid);

num_records = floor(length(raw) / RECORD_SIZE);
if num_records == 0
    error('File has no complete records.');
end

raw = raw(1 : num_records * RECORD_SIZE);
raw = reshape(raw, RECORD_SIZE, num_records);

time_ms = double(typecast(reshape(raw(1:4,  :), 1, []), 'uint32'))';
accX    = double(typecast(reshape(raw(5:8,  :), 1, []), 'single'))';
accY    = double(typecast(reshape(raw(9:12, :), 1, []), 'single'))';
accZ    = double(typecast(reshape(raw(13:16,:), 1, []), 'single'))';
rate_hz = double(typecast(reshape(raw(17:18,:), 1, []), 'uint16'))';

time_s = time_ms / 1000;
fprintf('  > Read %d records. Duration: %.3f s to %.3f s\n', num_records, time_s(1), time_s(end));

% --- Plot full time domain data
hFig = figure('Name', 'Full Time Domain - Choose Crop Range', 'NumberTitle', 'off');

subplot(3,1,1);
plot(time_s, accX, 'b', 'LineWidth', 0.8); grid on;
title('AccX'); xlabel('Time (s)'); ylabel('Acceleration');

subplot(3,1,2);
plot(time_s, accY, 'r', 'LineWidth', 0.8); grid on;
title('AccY'); xlabel('Time (s)'); ylabel('Acceleration');

subplot(3,1,3);
plot(time_s, accZ, 'g', 'LineWidth', 0.8); grid on;
title('AccZ'); xlabel('Time (s)'); ylabel('Acceleration');

sgtitle(sprintf('Full Data: %.3f s  to  %.3f s   |   Inspect plots, then click "Set Crop Range"', time_s(1), time_s(end)));

% --- Add button to figure — pauses script until clicked
uicontrol('Parent', hFig, ...
    'Style', 'pushbutton', ...
    'String', 'Set Crop Range', ...
    'Units', 'normalized', ...
    'Position', [0.38 0.01 0.24 0.04], ...
    'FontSize', 11, 'FontWeight', 'bold', ...
    'BackgroundColor', [0.18 0.55 0.90], ...
    'ForegroundColor', 'white', ...
    'Callback', @(~,~) uiresume(hFig));

uiwait(hFig);  % Pause here — script resumes when button is clicked

% Check if figure was closed without clicking the button
if ~ishandle(hFig)
    disp('Figure closed without cropping. Exiting.');
    return;
end

% --- Ask user for crop range
answer = inputdlg( ...
    {sprintf('Start Time (s)     [available: %.3f  to  %.3f]', time_s(1), time_s(end)), ...
     sprintf('End Time   (s)     [available: %.3f  to  %.3f]', time_s(1), time_s(end))}, ...
    'Set Crop Range', 1, ...
    {sprintf('%.3f', time_s(1)), sprintf('%.3f', time_s(end))});

if isempty(answer)
    disp('Cancelled. Exiting.');
    return;
end

t_start = str2double(answer{1});
t_end   = str2double(answer{2});

if isnan(t_start) || isnan(t_end) || t_start >= t_end || ...
   t_start < time_s(1) || t_end > time_s(end)
    errordlg(sprintf('Invalid range. Values must be between %.3f and %.3f s, with Start < End.', ...
        time_s(1), time_s(end)), 'Input Error');
    return;
end

% --- Crop
crop_mask = (time_s >= t_start) & (time_s <= t_end);
n_crop = sum(crop_mask);
fprintf('  > Cropping to %.3f s - %.3f s  (%d records)\n', t_start, t_end, n_crop);

time_ms_crop = uint32(time_ms(crop_mask));
accX_crop    = single(accX(crop_mask));
accY_crop    = single(accY(crop_mask));
accZ_crop    = single(accZ(crop_mask));
rate_hz_crop = uint16(rate_hz(crop_mask));

% --- Choose save location
[~, base_name, ~] = fileparts(filename);
default_name = sprintf('%s_crop_%.1f-%.1fs.bin', base_name, t_start, t_end);
[save_name, save_path] = uiputfile('*.bin', 'Save cropped BIN file as', fullfile(path, default_name));
if isequal(save_name, 0)
    disp('Save cancelled. Exiting.');
    return;
end
save_fullpath = fullfile(save_path, save_name);

% --- Write BIN file (vectorised, no loop)
out_raw = zeros(RECORD_SIZE, n_crop, 'uint8');
out_raw(1:4,   :) = reshape(typecast(time_ms_crop(:)', 'uint8'), 4, n_crop);
out_raw(5:8,   :) = reshape(typecast(accX_crop(:)',    'uint8'), 4, n_crop);
out_raw(9:12,  :) = reshape(typecast(accY_crop(:)',    'uint8'), 4, n_crop);
out_raw(13:16, :) = reshape(typecast(accZ_crop(:)',    'uint8'), 4, n_crop);
out_raw(17:18, :) = reshape(typecast(rate_hz_crop(:)', 'uint8'), 2, n_crop);

fid = fopen(save_fullpath, 'wb');
if fid == -1
    error('Could not create output file: %s', save_fullpath);
end
fwrite(fid, out_raw(:), 'uint8');
fclose(fid);

fprintf('  > Saved: %s\n', save_fullpath);

% --- Preview cropped data
time_s_crop = double(time_ms_crop) / 1000;

figure('Name', 'Cropped Data Preview', 'NumberTitle', 'off');

subplot(3,1,1);
plot(time_s_crop, accX_crop, 'b', 'LineWidth', 0.8); grid on;
title('AccX (Cropped)'); xlabel('Time (s)'); ylabel('Acceleration');

subplot(3,1,2);
plot(time_s_crop, accY_crop, 'r', 'LineWidth', 0.8); grid on;
title('AccY (Cropped)'); xlabel('Time (s)'); ylabel('Acceleration');

subplot(3,1,3);
plot(time_s_crop, accZ_crop, 'g', 'LineWidth', 0.8); grid on;
title('AccZ (Cropped)'); xlabel('Time (s)'); ylabel('Acceleration');

sgtitle(sprintf('Cropped: %.3f s  to  %.3f s   |   %d records   |   Saved as: %s', ...
    t_start, t_end, n_crop, save_name));

fprintf('Done.\n');
