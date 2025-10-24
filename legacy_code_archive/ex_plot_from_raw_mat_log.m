clear; clc;
function add_to_path(directories)
    % Loop through the input directories and add them if not already in the path
    for i = 1:length(directories)
        dirName = directories{i};
        if ~contains(path, dirName)
            addpath(dirName);
        end
    end
end
add_to_path({'logs_mat', 'decoders'});

%%
% 0) Wczytanie .mat z surowymi danymi
path_to_raw_mat = "log_raw_20250814_172913.mat";
S = load(path_to_raw_mat);

% Oczekuję pól: raw_timestamp [N x 1 uint32], raw_id [N x 1 uint16], raw_data [N x 8 uint8]
N  = numel(S.raw_id);
ts = double(S.raw_timestamp(:));   % <-- jeżeli to ms, później użyj milliseconds(ts)

% 1) Przejście przez dekoder i zbudowanie długiej tabeli (t, key, val)
t_out   = [];          % double [M x 1]
key_out = strings(0);  % string [M x 1]
val_out = [];          % double [M x 1]

% Jeśli dekoder jest czysto funkcyjny, można zamienić na parfor
for i = 1:N
    decoded = cmmc_database_decoder(uint32(S.raw_id(i)), S.raw_data(i,:));

    % nazwa ramki
    frm = string(decoded.frame);

    % pola sygnałów
    sigNames = fieldnames(decoded.signals);
    for s = 1:numel(sigNames)
        sig   = string(sigNames{s});
        value = double(decoded.signals.(sigNames{s}));

        t_out(end+1,1)   = ts(i);
        key_out(end+1,1) = frm + "_" + sig;
        val_out(end+1,1) = value;
    end
end

% poprawne nazwy kolumnowe
key_out = matlab.lang.makeValidName(key_out);

[W, TT] = pivot_signals(t_out, key_out, val_out, 'ms');

disp("Kolumny (frame_signal):"); disp(string(W.Properties.VariableNames)');
return

%%
sig = "SERVO_POSITION_ADC_VOLTAGE";
figure; plot(W.t, W.(sig), 'LineWidth', 1.2); grid on;
xlabel('timestamp'); ylabel('value'); title("Sygnał: " + sig);
