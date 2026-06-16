function WL_init_callback()
%WL_INIT_CALLBACK Prepare and start the WingLoop Python side from Simulink.

    fprintf('[Simulink] Preparing simulation...\n');

    scelta_gust = questdlg('Do you want to include the gust?', ...
        'Gust Configuration', 'Yes', 'No', 'No');
    if isempty(scelta_gust)
        scelta_gust = 'No';
    end

    scelta_video = questdlg('Do you want to generate a video after the simulation?', ...
        'Video Configuration', 'Yes', 'No', 'No');
    if isempty(scelta_video)
        scelta_video = 'No';
    end

    simulink_case_path = resolve_base_variable_or_model_path( ...
        'WL_SimulinkCasePath');
    matlab_utilities_path = resolve_matlab_utilities_path(simulink_case_path);
    config_folder = resolve_config_folder(simulink_case_path);

    if exist(config_folder, 'dir') ~= 7
        mkdir(config_folder);
    end

    file_inputs = fullfile(config_folder, 'python_inputs.txt');

    fid = fopen(file_inputs, 'w');
    if fid < 0
        error('Unable to open python input file for writing: %s', file_inputs);
    end
    cleanup_obj = onCleanup(@() fclose(fid));

    fprintf(fid, '1\n'); % Controller choice: 1 (LQI).
    if strcmp(scelta_gust, 'Yes')
        fprintf(fid, 'y\n');
    else
        fprintf(fid, 'n\n');
    end

    if strcmp(scelta_video, 'Yes')
        fprintf(fid, 'y\ngif\nmedium\nY\n');
    else
        fprintf(fid, 'n\n');
    end

    clear cleanup_obj;

    conda_env = resolve_conda_env();
    start_python_server(simulink_case_path, matlab_utilities_path, ...
        config_folder, conda_env);
end


function path_value = resolve_base_variable_or_model_path(variable_name)
    if evalin('base', sprintf('exist(''%s'', ''var'')', variable_name))
        path_value = evalin('base', variable_name);
        path_value = char(path_value);
        return;
    end

    model_file = get_param(bdroot, 'FileName');
    if isempty(model_file)
        error(['%s is not defined and the Simulink model has no file path. ' ...
            'Start the simulation from WingLoop_Simulink_Testrun.m.'], ...
            variable_name);
    end

    path_value = fileparts(model_file);
end


function matlab_utilities_path = resolve_matlab_utilities_path(simulink_case_path)
    if evalin('base', 'exist(''WL_MatlabUtilitiesPath'', ''var'')')
        matlab_utilities_path = evalin('base', 'WL_MatlabUtilitiesPath');
        matlab_utilities_path = char(matlab_utilities_path);
        return;
    end

    probe = simulink_case_path;
    while true
        candidate = fullfile(probe, 'MatlabUtilities');
        if exist(candidate, 'dir') == 7
            matlab_utilities_path = candidate;
            return;
        end

        parent = fileparts(probe);
        if strcmp(parent, probe)
            break;
        end
        probe = parent;
    end

    error(['Unable to locate MatlabUtilities. Start the simulation from ' ...
        'WingLoop_Simulink_Testrun.m or set wingloop_library_path there.']);
end


function config_folder = resolve_config_folder(simulink_case_path)
    if evalin('base', 'exist(''WL_ConfigFolder'', ''var'')')
        config_folder = evalin('base', 'WL_ConfigFolder');
        config_folder = char(config_folder);
    else
        config_folder = fullfile(simulink_case_path, 'config');
    end
end


function conda_env = resolve_conda_env()
    if evalin('base', 'exist(''WL_CondaEnv'', ''var'')')
        conda_env = evalin('base', 'WL_CondaEnv');
    else
        conda_env = "WINGLOOP";
    end

    conda_env = strtrim(string(conda_env));
    if strlength(conda_env) == 0
        conda_env = "WINGLOOP";
    end

    conda_env = char(conda_env);
end


function start_python_server(simulink_case_path, matlab_utilities_path, ...
    config_folder, conda_env)

    log_file = fullfile(simulink_case_path, 'wingloop_python_server.log');
    config_file = fullfile(config_folder, 'sim_config.json');
    input_file = fullfile(config_folder, 'python_inputs.txt');
    controller_file = fullfile(matlab_utilities_path, 'controller_wingloop.py');

    fprintf('[Simulink] Python server log: %s\n', log_file);

    if ispc
        case_path_wsl = windows_path_to_wsl_path(simulink_case_path);
        log_file_wsl = windows_path_to_wsl_path(log_file);
        config_file_wsl = windows_path_to_wsl_path(config_file);
        input_file_wsl = windows_path_to_wsl_path(input_file);
        controller_file_wsl = windows_path_to_wsl_path(controller_file);

        launch_cmd = build_python_launch_command(case_path_wsl, ...
            controller_file_wsl, config_file_wsl, input_file_wsl, conda_env);
        launch_cmd = sprintf('%s > %s 2>&1; exec bash', ...
            launch_cmd, shell_quote_for_bash(log_file_wsl));
        cmd_wsl = sprintf('start "WingLoop Python Server" wsl -e bash -lc %s', ...
            shell_quote_for_cmd(launch_cmd));
        system(cmd_wsl);
    else
        launch_cmd = build_python_launch_command(simulink_case_path, ...
            controller_file, config_file, input_file, conda_env);
        cmd_unix = sprintf('bash -lc %s > %s 2>&1 &', ...
            shell_quote_for_bash(launch_cmd), shell_quote_for_bash(log_file));
        system(cmd_unix);
    end
end


function launch_cmd = build_python_launch_command(working_path, ...
    controller_file, config_file, input_file, conda_env)

    launch_cmd = sprintf([ ...
        'cd %s && ' ...
        'echo "[WingLoop] Starting Python server from $(pwd)" && ' ...
        'echo "[WingLoop] Conda environment:" %s && ' ...
        'if command -v conda >/dev/null 2>&1; then ' ...
            'CONDA_BASE=$(conda info --base); ' ...
        'elif [ -x "$HOME/miniconda3/bin/conda" ]; then ' ...
            'CONDA_BASE=$("$HOME/miniconda3/bin/conda" info --base); ' ...
        'elif [ -x "$HOME/anaconda3/bin/conda" ]; then ' ...
            'CONDA_BASE=$("$HOME/anaconda3/bin/conda" info --base); ' ...
        'else ' ...
            'echo "[WingLoop] ERROR: conda executable not found."; exit 127; ' ...
        'fi && ' ...
        'if [ ! -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then ' ...
            'echo "[WingLoop] ERROR: conda.sh not found in $CONDA_BASE."; exit 127; ' ...
        'fi && ' ...
        '. "$CONDA_BASE/etc/profile.d/conda.sh" && ' ...
        'conda activate %s && ' ...
        'WINGLOOP_SIM_CONFIG=%s python3 -u %s < %s'], ...
        shell_quote_for_bash(working_path), ...
        shell_quote_for_bash(conda_env), ...
        shell_quote_for_bash(conda_env), ...
        shell_quote_for_bash(config_file), ...
        shell_quote_for_bash(controller_file), ...
        shell_quote_for_bash(input_file));
end


function path_wsl = windows_path_to_wsl_path(path_in)
    path_wsl = strrep(path_in, '\', '/');

    token = regexp(path_wsl, '^//wsl\.localhost/[^/]+(/.*)$', ...
        'tokens', 'once');
    if isempty(token)
        token = regexp(path_wsl, '^//wsl\$/[^/]+(/.*)$', ...
            'tokens', 'once');
    end

    if ~isempty(token)
        path_wsl = token{1};
        return;
    end

    [status, converted] = system(sprintf('wsl wslpath -a %s', ...
        shell_quote_for_cmd(path_in)));
    if status == 0
        path_wsl = strtrim(converted);
    end
end


function quoted = shell_quote_for_bash(text)
    quoted = ['''' strrep(text, '''', '''"''"''') ''''];
end


function quoted = shell_quote_for_cmd(text)
    quoted = ['"' strrep(text, '"', '\"') '"'];
end
