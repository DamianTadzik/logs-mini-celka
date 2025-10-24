function export_plotjuggler_json(TT, outputFile)
%EXPORT_PLOTJUGGLER_JSON Export timetable TT to PlotJuggler JSON
%
%   TT: timetable, where RowTimes are datetime or duration
%   outputFile: target JSON file name

    % Convert time to seconds relative to first sample
    if isdatetime(TT.Properties.RowTimes)
        t_sec = seconds(TT.Properties.RowTimes - TT.Properties.RowTimes(1));
    else
        t_sec = seconds(TT.Properties.RowTimes);
        t_sec = t_sec - t_sec(1);
    end

    % Prepare structure
    jsonData.version = 1;
    jsonData.streams = struct();

    vars = TT.Properties.VariableNames;
    for v = 1:numel(vars)
        name = vars{v};
        y = TT.(name);
        pairs = [t_sec, y];
        jsonData.streams.(name).values = pairs;
    end

    % Encode and save
    jsonStr = jsonencode(jsonData);
    fid = fopen(outputFile, 'w');
    if fid < 0
        error("Cannot open file for writing: %s", outputFile);
    end
    fwrite(fid, jsonStr, 'char');
    fclose(fid);

    fprintf("✅ Exported PlotJuggler JSON to %s\n", outputFile);
end
