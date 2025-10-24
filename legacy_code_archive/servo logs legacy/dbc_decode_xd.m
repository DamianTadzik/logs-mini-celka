clear
%% Config
% logFile = 'LOG000.TXT';
logFile = 'LOG.TXT';
dbcFile = 'mini_celka.dbc'; % Twój DBC

%% Wczytanie linii z pliku
lines = readlines(logFile);
lines = lines(~startsWith(lines,"#")); % pomiń nagłówki

%% Parsowanie regexem
% Format: HH:MM:SS,KKK;ID;DATA
% np: 02:15:03,248;40;8403B90C02000000
expr = '^(?<time>(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d,\d{3});(?<id>[0-9A-Fa-f]{2});(?<data>[0-9A-Fa-f]{16})$';

tokens = regexp(lines, expr, 'names');

% Usuń puste linie
tokens = tokens(~cellfun(@isempty,tokens));

%% Zamiana na tablicę
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
disp("canTT is ready!")

%% Call mex

% Extract all unique timestamps
uniqueTimes = unique(canTT.Time);

% Preallocate timetable with unique times and no variables
sigTT = timetable('Size',[numel(uniqueTimes) 0], 'RowTimes', uniqueTimes);

for i = 1:height(canTT)
    try
        decoded = cmmc_database_decoder(canTT.ID(i), canTT.Data(i,:));
        fields = fieldnames(decoded.signals)

        % Find row index for this frame's timestamp
        rowIdx = find(sigTT.Time == canTT.Time(i));

        % Add columns if missing, assign values at rowIdx
        for f = 1:numel(fields)
            sigName = fields{f};
            if ~ismember(sigName, sigTT.Properties.VariableNames)
                % Add new column filled with NaN
                sigTT.(sigName) = nan(height(sigTT),1);
            end
            sigTT.(sigName)(rowIdx) = decoded.signals.(sigName);
        end

    catch ME
        disp(ME);
    end
end


%% Call python from matlab, yooooo!
% % Import cantools
% cantools = py.importlib.import_module('cantools');
% 
% % Load DBC
% db = cantools.database.load_file(dbcFile);
% 
% % Extract all unique timestamps
% uniqueTimes = unique(canTT.Time);
% 
% % Preallocate timetable with unique times and no variables
% sigTT = timetable('Size',[numel(uniqueTimes) 0], 'RowTimes', uniqueTimes);
% 
% % Loop over all CAN frames
% for i = 1:height(canTT)
%     try
%         % Pass CAN ID as int32 (Python int)
%         canID = int32(canTT.ID(i));
% 
%         % Pass CAN data as a row uint8 vector converted to py.bytes
%         % canData = py.bytes(uint8(canTT.Data(i,:)));
%         canData = py.bytes(py.list(num2cell(uint8(canTT.Data(i,:)))));
% 
% 
%         decoded = db.decode_message(canID, canData);
%         decoded = struct(decoded);
% 
%         % Convert Python numerics to MATLAB types
%         fields = fieldnames(decoded);
%         for f = 1:numel(fields)
%             val = decoded.(fields{f});
%             if isa(val, 'py.int') || isa(val, 'py.float')
%                 val = double(val);
%             end
%             decoded.(fields{f}) = val;
%         end
% 
%         % Find row index for this frame's timestamp
%         rowIdx = find(sigTT.Time == canTT.Time(i));
% 
%         % Add columns if missing, assign values at rowIdx
%         for f = 1:numel(fields)
%             sigName = fields{f};
%             if ~ismember(sigName, sigTT.Properties.VariableNames)
%                 % Add new column filled with NaN
%                 sigTT.(sigName) = nan(height(sigTT),1);
%             end
%             sigTT.(sigName)(rowIdx) = decoded.(sigName);
%         end
% 
%     catch ME
%         if contains(ME.message, 'KeyError')
%             % handle unknown IDs
%             continue
%         else
%             rethrow(ME);
%         end
%     end
% end
disp("sigTT is ready!")

%% Podgląd sygnałów
disp(head(sigTT))

%% Wykres SETPOINT i ADC_RAW
figure;
yyaxis left
plot(sigTT.Time, sigTT.SETPOINT, 'b-'); hold on;
ylabel('Setpoint [us]')

yyaxis right
plot(sigTT.Time, sigTT.ADC_RAW, 'r-');
ylabel('ADC RAW')

xlabel('Czas')
grid on
title('Dekodowane sygnały z CAN')
