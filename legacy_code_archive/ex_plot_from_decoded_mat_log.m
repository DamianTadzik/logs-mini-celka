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
add_to_path({'logs_mat'});

%%
% 0) Input
path_to_decoded_mat = "log_decoded_20250814_172913.mat";
S = load(path_to_decoded_mat);

t   = double(S.dec_timestamp(:));
key = string(S.dec_frame(:)) + "_" + string(S.dec_signal(:));
val = double(S.dec_value(:));

[W, TT] = pivot_signals(t, key, val, 'ms');

disp("Kolumny (frame_signal):"); disp(string(W.Properties.VariableNames)');

return
%% Plot
sig = "SERVO_POSITION_SETPOINT";
figure; plot(W.t, W.(sig), 'LineWidth', 1.2); grid on;
xlabel('timestamp'); ylabel('value'); title("Sygnał: " + sig);
