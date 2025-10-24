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
add_to_path({'logs_txt', 'decoders'});

%% Config
logFile = 'LOG001.TXT';

%% Wczytanie linii z pliku
lines = readlines(logFile);
lines = lines(~startsWith(lines,"#")); % pomiń nagłówki

% Parsowanie regexem
% Format: HH:MM:SS,KKK;ID;DATA
% np: 02:15:03,248;40;8403B90C02000000
expr = '^(?<time>(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d,\d{3});(?<id>[0-9A-Fa-f]{2});(?<data>[0-9A-Fa-f]{16})$';
tokens = regexp(lines, expr, 'names');
% Usuń puste linie
tokens = tokens(~cellfun(@isempty,tokens));

% Zamiana na tablicę
n = numel(tokens);
Time = NaT(n,1);
ID = zeros(n,1,'uint32');
Data = zeros(n,8,'uint8');

for i = 1:n
    % Timestamp
    Time(i) = datetime(tokens{i}.time,'InputFormat','HH:mm:ss,SSS');
    
    % CAN ID
    ID(i) = hex2dec(tokens{i}.id);
    
    % Data na bajty
    hexStr = tokens{i}.data;
    bytes = reshape(uint8(sscanf(hexStr,'%2x').'),1,[]);
    Data(i,1:numel(bytes)) = bytes;
end

canTT = timetable(Time, ID, Data);
% disp("canTT is ready!")

%% Call mex

t_out = NaT(0,1); key_out = strings(0,1); val_out = [];
for i = 1:height(canTT)
    try
        decoded = cmmc_database_decoder(canTT.ID(i), canTT.Data(i,:));
        frm = string(decoded.frame);
        fields = fieldnames(decoded.signals);
        
        for f = 1:numel(fields)
            sig  = string(fields{f});
            t_out(end+1,1)  = canTT.Time(i);      
            key_out(end+1,1)= frm + "_" + sig;
            val_out(end+1,1)= double(decoded.signals.(fields{f}));
        end
    catch ME
        disp(ME);
    end
end

[W, TT] = pivot_signals(t_out, key_out, val_out, 'datetime');
disp("Kolumny (frame_signal):"); disp(string(W.Properties.VariableNames)');
return

%%
sig = "SERVO_POSITION_ADC_VOLTAGE";
figure; plot(W.t, W.(sig), 'LineWidth', 1.2); grid on;
xlabel('timestamp'); ylabel('value'); title("Sygnał: " + sig);
