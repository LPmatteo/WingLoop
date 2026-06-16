function WL_init_callback()
%WL_INIT_CALLBACK Prepare and start the WingLoop Python side from Simulink.
%
% The repository path must not be hardcoded in WL_test.slx. WL_main sets
% WL_TestrunPath before starting the simulation; if the model is opened
% directly, this function falls back to the model file location.

    fprintf('[Simulink] Preparazione simulazione...\n');

    scelta_gust = questdlg('Vuoi includere la gust?', ...
        'Configurazione Raffica', 'Si', 'No', 'No');
    if isempty(scelta_gust)
        scelta_gust = 'No';
    end

    scelta_video = questdlg('Vuoi generare il video MP4 a fine simulazione?', ...
        'Configurazione Video', 'Si', 'No', 'No');
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
    if strcmp(scelta_gust, 'Si')
        fprintf(fid, 's\n');
    else
        fprintf(fid, 'n\n');
    end

    if strcmp(scelta_video, 'Si')
        fprintf(fid, 's\ngif\nmedium\nY\n');
    else
        fprintf(fid, 'n\n');
    end

    clear cleanup_obj;

    start_python_server(percorso);
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


function start_python_server(percorso)
    if ispc
        percorso_wsl = windows_path_to_wsl_path(percorso);
        cmd_wsl = sprintf(['start "WingLoop Python Server" wsl -e bash -ic ' ...
            '"cd %s && conda activate WINGLOOP && ' ...
            'python3 controller_wingloop.py < python_inputs.txt; exec bash"'], ...
            shell_quote_for_bash(percorso_wsl));
        system(cmd_wsl);
    else
        cmd_unix = sprintf(['bash -ic "cd %s && conda activate WINGLOOP && ' ...
            'python3 controller_wingloop.py < python_inputs.txt" &'], ...
            shell_quote_for_bash(percorso));
        system(cmd_unix);
    end
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
