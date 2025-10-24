function [W, TT] = import_can_signals(file_path)
    [~,name,ext] = fileparts(file_path);
    switch lower(ext)
        case '.mat'
            if contains(name, 'dec','IgnoreCase',true) || contains(name, 'decoded','IgnoreCase',true)
                [W, TT] = import_can_signals_from_decoded_mat(file_path);
            elseif contains(name, 'raw','IgnoreCase',true)
                [W, TT] = import_can_signals_from_raw_mat(file_path);
            else
                error('Nieznany format pliku MAT: %s', file_path);
            end
        case '.txt'
            [W, TT] = import_can_signals_from_raw_txt(file_path);
        otherwise
            error('Nieobsługiwane rozszerzenie: %s', ext);
    end
end

function [W, TT] = import_can_signals_from_decoded_mat(path_to_decoded_mat)
    S = load(path_to_decoded_mat);
    
    t   = double(S.dec_timestamp(:));
    key = string(S.dec_frame(:)) + "_" + string(S.dec_signal(:));
    val = double(S.dec_value(:));
    
    [W, TT] = pivot_signals(t, key, val, 'ms');
end

function [W, TT] = import_can_signals_from_raw_mat(path_to_raw_mat)
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
end

% function [W, TT] = import_can_signals_from_raw_txt(logFile)
%     lines = readlines(logFile);
%     lines = lines(~startsWith(lines,"#")); % pomiń nagłówki
% 
%     % Parsowanie regexem
%     % Format: HH:MM:SS,KKK;ID;DATA
%     % np: 02:15:03,248;40;8403B90C02000000
%     expr = '^(?<time>(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d,\d{3});(?<id>[0-9A-Fa-f]{2});(?<data>[0-9A-Fa-f]{16})$';
%     tokens = regexp(lines, expr, 'names');
%     % Usuń puste linie
%     tokens = tokens(~cellfun(@isempty,tokens));
% 
%     % Zamiana na tablicę
%     n = numel(tokens);
%     Time = NaT(n,1);
%     ID = zeros(n,1,'uint32');
%     Data = zeros(n,8,'uint8');
% 
%     for i = 1:n
%         % Timestamp
%         Time(i) = datetime(tokens{i}.time,'InputFormat','HH:mm:ss,SSS');
% 
%         % CAN ID
%         ID(i) = hex2dec(tokens{i}.id);
% 
%         % Data na bajty
%         hexStr = tokens{i}.data;
%         bytes = reshape(uint8(sscanf(hexStr,'%2x').'),1,[]);
%         Data(i,1:numel(bytes)) = bytes;
%     end
%     canTT = timetable(Time, ID, Data);
%     % disp("canTT is ready!")
% 
%     % Call mex
%     t_out = NaT(0,1); key_out = strings(0,1); val_out = [];
%     for i = 1:height(canTT)
%         try
%             decoded = cmmc_database_decoder(canTT.ID(i), canTT.Data(i,:));
%             frm = string(decoded.frame);
%             fields = fieldnames(decoded.signals);
% 
%             for f = 1:numel(fields)
%                 sig  = string(fields{f});
%                 t_out(end+1,1)  = canTT.Time(i);      
%                 key_out(end+1,1)= frm + "_" + sig;
%                 val_out(end+1,1)= double(decoded.signals.(fields{f}));
%             end
%         catch ME
%             disp(ME);
%             disp(canTT.ID(i));
%         end
%     end
% 
%     [W, TT] = pivot_signals(t_out, key_out, val_out, 'datetime');
% end
function [W, TT, canTT] = import_can_signals_from_raw_txt(logFile)
%IMPORT_CAN_SIGNALS_FROM_RAW_TXT
%   Reads a raw CAN text log and decodes it using cmmc_database_decoder.
%   Produces both timetable (TT) and wide table (W), and automatically
%   exports a PlotJuggler-compatible JSON file next to the log.

    fprintf("📄 Reading log file: %s\n", logFile);
    lines = readlines(logFile);
    lines = lines(~startsWith(lines, "#") & strlength(lines) > 0);

    % Example line format:
    % 02:15:03,248;40;8403B90C02000000
    expr = '^(?<time>(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d,\d{3});(?<id>[0-9A-Fa-f]{2});(?<data>[0-9A-Fa-f]{16})$';
    tokens = regexp(lines, expr, 'names');
    tokens = tokens(~cellfun(@isempty, tokens));
    n = numel(tokens);
    if n == 0
        error("No valid CAN frames detected in file: %s", logFile);
    end

    % --- Preallocate parsed frame data
    Time = NaT(n,1);
    ID   = zeros(n,1,'uint32');
    Data = zeros(n,8,'uint8');

    for i = 1:n
        Time(i) = datetime(tokens{i}.time,'InputFormat','HH:mm:ss,SSS');
        ID(i)   = hex2dec(tokens{i}.id);
        bytes   = uint8(sscanf(tokens{i}.data,'%2x').');
        Data(i,1:numel(bytes)) = bytes;
    end
    canTT = timetable(Time, ID, Data);

    % --- Preallocate decoded arrays
    maxSignals = height(canTT) * 10; % generous upper bound
    t_out   = NaT(maxSignals, 1);
    key_out = strings(maxSignals, 1);
    val_out = zeros(maxSignals, 1);
    idx = 0;

    % --- Decode efficiently
    fprintf("⚙️  Decoding %d CAN frames...\n", height(canTT));
    for i = 1:height(canTT)
        try
            decoded = cmmc_database_decoder(canTT.ID(i), canTT.Data(i,:));
            if isempty(decoded) || isempty(decoded.signals), continue; end

            fields = fieldnames(decoded.signals);
            vals   = struct2array(decoded.signals);
            vals = double(vals(:));
            vals(isnan(vals)) = NaN; % lub NaN, jak wolisz
            nSig   = numel(fields);

            t_out(idx+1:idx+nSig)   = repmat(canTT.Time(i), nSig, 1);
            key_out(idx+1:idx+nSig) = decoded.frame + "_" + string(fields);
            val_out(idx+1:idx+nSig) = vals;
            idx = idx + nSig;
        catch
            % If you want to debug errors:
            % fprintf("⚠️  Error decoding ID %d: %s\n", canTT.ID(i), ME.message);
            continue;
        end
    end

    % --- Trim to actual size
    t_out   = t_out(1:idx);
    key_out = key_out(1:idx);
    val_out = val_out(1:idx);

    % --- Pivot to wide format
    [W, TT] = pivot_signals(t_out, key_out, val_out, 'datetime');

    % --- Export JSON automatically
    jsonPath = replace(logFile, ".txt", "_plotjuggler.json");
    export_plotjuggler_json(TT, jsonPath);
end


function export_plotjuggler_json(TT, outputFile)
%EXPORT_PLOTJUGGLER_JSON  Save timetable as PlotJuggler JSON file

    fprintf("🧾 Exporting PlotJuggler JSON → %s\n", outputFile);

    % Relative time in seconds
    if isdatetime(TT.Properties.RowTimes)
        t_sec = seconds(TT.Properties.RowTimes - TT.Properties.RowTimes(1));
    else
        t_sec = seconds(TT.Properties.RowTimes);
        t_sec = t_sec - t_sec(1);
    end

    vars = TT.Properties.VariableNames;
    jsonData.version = 1;
    jsonData.streams = struct();

    for v = 1:numel(vars)
        y = TT.(vars{v});
        jsonData.streams.(vars{v}).values = [t_sec, y];
    end

    % JSON encode & write
    jsonStr = jsonencode(jsonData);
    fid = fopen(outputFile, 'w');
    if fid < 0
        error("Cannot open file for writing: %s", outputFile);
    end
    fwrite(fid, jsonStr, 'char');
    fclose(fid);

    fprintf("✅ Done! JSON saved (%d signals)\n", numel(vars));
end



function [W, TT] = pivot_signals(t, key, val, timeUnit)
%PIVOT_SIGNALS  zamienia (t, key, val) -> szeroka tabela W oraz timetable TT
%
% t        : double/datetime/duration (Nx1) — timestamp
% key      : string/cellstr (Nx1)           — nazwa kolumny (frame_signal)
% val      : double (Nx1)                   — wartość
% timeUnit : 'ms'|'s'|'datetime' (opcjonalne; domyślnie 'ms' dla double)
%
% W  : tabela z kolumną t + kolumny sygnałów
% TT : timetable (jeśli t jest double/duration; jeśli datetime — TT z datetime)

    arguments
        t
        key
        val double
        timeUnit char {mustBeMember(timeUnit,{'ms','s','datetime'})} = ''
    end

    % Ujednolicenie wektorów
    t   = t(:); key = string(key(:)); val = val(:);

    % Zbuduj tabelę długą
    T = table(t, matlab.lang.makeValidName(key), val, ...
              'VariableNames', {'t','key','val'});

    % sanity check before unstack
    bad_idx = find(strlength(key)==0 | ismissing(key));
    if ~isempty(bad_idx)
        warning("⚠️ Found %d empty signal keys; removing them", numel(bad_idx));
        T(bad_idx,:) = [];
    end
    function y = safe_last(x)
        if isempty(x)
            y = NaN;
        else
            y = x(end);
        end
    end
    % Pivot z agregacją "ostatnia wartość"
    W = unstack(T, 'val', 'key', ...
                'GroupingVariables', 't', ...
                'AggregationFunction', @(x) safe_last(x));
    W = sortrows(W, 't');

    % Timetable
    if isdatetime(W.t)
        TT = table2timetable(W, 'RowTimes', 't');
    else
        % auto-detekcja jednostki czasu dla double
        if isempty(timeUnit)
            timeUnit = 'ms'; % u Ciebie zazwyczaj ms
        end
        switch timeUnit
            case 'ms',  rowTimes = milliseconds(W.t);
            case 's',   rowTimes = seconds(W.t);
            case 'datetime' % raczej nie trafi tu, ale dla spójności
                rowTimes = W.t;
        end
        TT = table2timetable(W, 'RowTimes', rowTimes);
    end
end
