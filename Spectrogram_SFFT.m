% =========================================================================
% Variable-Pitch Quadrotor - Combined Vibration Analysis (FFT + Spectrogram)
% =========================================================================

% --- 1. File Selection & Binary Parsing ---
[filename, path] = uigetfile('*.bin', 'Select BIN file');
if isequal(filename, 0), disp('No file selected.'); return; end
fullpath = fullfile(path, filename);

RECORD_SIZE = 18;
fid = fopen(fullpath, 'rb');
if fid == -1, error('Could not open file.'); end
raw = fread(fid, Inf, 'uint8=>uint8');
fclose(fid);

num_records = floor(length(raw) / RECORD_SIZE);
raw = reshape(raw(1 : num_records * RECORD_SIZE), RECORD_SIZE, num_records);

% Extract Data Fields
time_ms = double(typecast(reshape(raw(1:4, :), 1, []), 'uint32'))';
accX    = double(typecast(reshape(raw(5:8, :), 1, []), 'single'))';

% --- 2. Timing and Sample Rate ---
time_s = time_ms / 1000;
Fs = 1 / mean(diff(time_s)); 
fprintf('Processing %s: Fs = %.2f Hz\n', filename, Fs);

% =========================================================================
% FIGURE 1: 10-Segmented Overlaid FFT
% =========================================================================
numSegments = 10;
samplesPerSeg = floor(length(accX) / numSegments);
colors = jet(numSegments); 

figure('Color', 'w', 'Name', ['Segmented FFT: ', filename], 'Position', [100 100 800 500]);
hold on; grid on;

for s = 1:numSegments
    % Extract Segment
    idxStart = (s-1) * samplesPerSeg + 1;
    idxEnd = s * samplesPerSeg;
    segData = accX(idxStart:idxEnd);
    
    % Compute FFT
    N = length(segData);
    X = fft(segData);
    f = Fs * (0:(N/2)) / N;
    magX = abs(X / N); 
    magX = magX(1:N/2+1); 
    magX(2:end-1) = 2 * magX(2:end-1);
    
    % Smooth for better visibility
    smoothMagX = movmean(magX, 10);
    
    % Plot
    plot(f, smoothMagX, 'Color', colors(s,:), 'LineWidth', 1.2, ...
        'DisplayName', sprintf('Seg %d (%.1fs - %.1fs)', s, (idxStart/Fs), (idxEnd/Fs)));
end

title(['Overlay of 10 Flight Segments - AccX (', filename, ')']);
xlabel('Frequency (Hz)');
ylabel('Magnitude (m/s^2)');
xlim([0 60]); 
ylim([0 170]);
legend('Location', 'northeastoutside');

% =========================================================================
% FIGURE 2: High-Resolution "White-Hot" Spectrogram
% =========================================================================
% Spectrogram Configuration
window = 1024;      
noverlap = 512;     
nfft = 4096;        
[S, F, T, P] = spectrogram(accX, window, noverlap, nfft, Fs, 'yaxis');
Mag_Linear = sqrt(P); 

% Custom "White-Hot" Colormap Logic
custom_map = [
    interp1([0, 100], [0 0 0.1; 0 0.15 0.5], linspace(0, 100, 150)); 
    interp1([100, 140], [0 0.15 0.5; 1 0.2 0], linspace(100, 140, 30)); 
    interp1([140, 180, 210, 300], ...
            [1 0 0; 1 0 0.5; 1 0 1; 1 1 1], ...
             linspace(140, 300, 76)); 
];

figure('Name', 'Extreme Vibe Spectrogram (300 Limit)', 'Color', 'k', 'Position', [150 150 1200 600]);
imagesc(T, F, Mag_Linear);
axis xy;
colormap(custom_map);
caxis([0 300]); 

% Formatting
ylim([0 40]); 
ylabel('Frequency (Hz)', 'Color', 'w', 'FontSize', 12);
xlabel('Flight Time (seconds)', 'Color', 'w', 'FontSize', 12);
title(['AccX High-Res Spectrum: ', filename, ' (White > 300 m/s^2)'], 'Color', 'w', 'FontSize', 14);
set(gca, 'Color', 'k', 'XColor', 'w', 'YColor', 'w', 'FontSize', 10);
set(gca, 'GridColor', [0.4 0.4 0.4], 'GridAlpha', 0.6);
grid on;

h = colorbar;
set(h, 'Color', 'w', 'FontSize', 10);
ylabel(h, 'Magnitude (m/s^2)', 'Color', 'w', 'FontSize', 11);

fprintf('Analysis Complete.\n');
fprintf('Figure 1: Comparison of flight phases (Blue=Start, Red=End).\n');
fprintf('Figure 2: Peak vibration hotspots (White exceeds 300 m/s^2).\n');