function WL_init_callback()
%WL_INIT_CALLBACK Prepare and start the WingLoop Python side from Simulink.
%
% The repository path must not be hardcoded in WL_test.slx. WL_main sets
% WL_TestrunPath before starting the simulation; if the model is opened
% directly, this function falls back to the model file location.

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

    percorso = resolve_wingloop_testrun_path();
    file_inputs = fullfile(percorso, 'python_inputs.txt');

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
    start_python_server(percorso, conda_env);
end


function percorso = resolve_wingloop_testrun_path()
    if evalin('base', 'exist(''WL_TestrunPath'', ''var'')')
        percorso = evalin('base', 'WL_TestrunPath');
        return;
    end

    model_file = get_param(bdroot, 'FileName');
    if isempty(model_file)
        error(['WL_TestrunPath is not defined and the Simulink model has ' ...
            'no file path. Start the simulation from WL_main.m.']);
    end

    simulink_controller_path = fileparts(model_file);
    percorso = fileparts(simulink_controller_path);
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


function start_python_server(percorso, conda_env)
    log_file = fullfile(percorso, 'wingloop_python_server.log');
    fprintf('[Simulink] Python server log: %s\n', log_file);

    if ispc
        percorso_wsl = windows_path_to_wsl_path(percorso);
        log_file_wsl = windows_path_to_wsl_path(log_file);
        launch_cmd = build_python_launch_command(percorso_wsl, conda_env);
        launch_cmd = sprintf('%s > %s 2>&1; exec bash', ...
            launch_cmd, shell_quote_for_bash(log_file_wsl));
        cmd_wsl = sprintf('start "WingLoop Python Server" wsl -e bash -lc %s', ...
            shell_quote_for_cmd(launch_cmd));
        system(cmd_wsl);
    else
        launch_cmd = build_python_launch_command(percorso, conda_env);
        cmd_unix = sprintf('bash -lc %s > %s 2>&1 &', ...
            shell_quote_for_bash(launch_cmd), shell_quote_for_bash(log_file));
        system(cmd_unix);
    end
end


function launch_cmd = build_python_launch_command(percorso, conda_env)
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
        'python3 controller_wingloop.py < python_inputs.txt'], ...
        shell_quote_for_bash(percorso), ...
        shell_quote_for_bash(conda_env), ...
        shell_quote_for_bash(conda_env));
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
