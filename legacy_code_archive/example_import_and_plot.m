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
add_to_path({'logs_mat', 'logs_txt', 'decoders'});

%% Define the path to the log file
% path_to_any_log_file = "logs_mat\log_decoded_20250814_172913.mat";
% path_to_any_log_file = "logs_mat\log_raw_20250817_234006.mat";
% path_to_any_log_file = "logs_txt\LOG001.TXT";

path_to_any_log_file = "F:\LOG009.TXT";

try
    [W, TT] = import_can_logs(path_to_any_log_file);
    disp(string(W.Properties.VariableNames)');
catch ME
    disp(ME);
    return
end

%%
plot(TT.t, TT.ACTUATOR_REAR_FOIL_FEEDBACK_CURRENT);

TT.t(end) - TT.t(1)