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

    % Pivot z agregacją "ostatnia wartość"
    W = unstack(T, 'val', 'key', ...
                'GroupingVariables', 't', ...
                'AggregationFunction', @(x) x(end));
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
