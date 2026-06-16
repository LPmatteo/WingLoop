%% ========================================================================
%  LOCAL FUNCTIONS
%  ========================================================================

function model_name = run_wingloop_simulink_setup( ...
    T_sim, Dt_asw, Dt_sim, Ts_control, tau, t_int, ...
    ASW_FILE, PNT_FILE, SET_FILE, STATE_FILE, GUST_FILE, ...
    ROM, FullModel, u_trim, ...
    model_name, model_file, wingloop_env, alias_aswing, ...
    wingloop_library_path, aswing_case_folder, simulink_case_path ...
)

    fprintf('\n==================================================\n');
    fprintf('WingLoop Simulink Setup\n');
    fprintf('==================================================\n');

    wingloop_env = normalize_text_setting(wingloop_env, "WINGLOOP");
    alias_aswing = normalize_text_setting(alias_aswing, "aswing");
    wingloop_library_path = char(strtrim(string(wingloop_library_path)));
    simulink_case_path = char(strtrim(string(simulink_case_path)));

    matlab_utilities_path = fullfile(wingloop_library_path, 'MatlabUtilities');
    if exist(matlab_utilities_path, 'dir') ~= 7
        error('MatlabUtilities folder not found: %s', matlab_utilities_path);
    end

    aswing_case_folder = resolve_aswing_case_folder( ...
        aswing_case_folder, simulink_case_path, wingloop_library_path);

    config_folder = fullfile(simulink_case_path, 'config');
    if exist(config_folder, 'dir') ~= 7
        mkdir(config_folder);
    end
    json_path = fullfile(config_folder, 'sim_config.json');

    addpath(matlab_utilities_path);
    assignin('base', 'WL_SimulinkCasePath', simulink_case_path);
    assignin('base', 'WL_MatlabUtilitiesPath', matlab_utilities_path);
    assignin('base', 'WL_ConfigFolder', config_folder);
    assignin('base', 'WL_CondaEnv', wingloop_env);

    %% --- Print Time Configuration ---
    fprintf('\n--- TIME CONFIGURATION ---\n');
    fprintf('T_sim      : %g s\n', T_sim);
    fprintf('Dt_ASWING  : %g s\n', Dt_asw);
    fprintf('Dt_Simulink: %g s\n', Dt_sim);
    fprintf('Ts_Control : %g s\n', Ts_control);
    fprintf('tau        : %g s\n', tau);
    fprintf('t_int      : %g s\n', t_int);

    %% --- Print ASWING Case Configuration ---
    fprintf('\n--- ASWING CASE CONFIGURATION ---\n');
    fprintf('ASWING alias : %s\n', alias_aswing);
    fprintf('Case folder  : %s\n', aswing_case_folder);
    fprintf('ASW file     : %s\n', ASW_FILE);
    fprintf('PNT file     : %s\n', PNT_FILE);
    fprintf('SET file     : %s\n', SET_FILE);
    fprintf('STATE file   : %s\n', STATE_FILE);
    fprintf('GUST file    : %s\n', GUST_FILE);

    %% --- Print Python Configuration ---
    fprintf('\n--- PYTHON CONFIGURATION ---\n');
    fprintf('Conda env    : %s\n', wingloop_env);
    fprintf('Config folder: %s\n', config_folder);

    %% --- Print Model Dimensions ---
    NumModalStates    = ROM.n_modal;
    NumPhysicalStates = FullModel.n_orig + FullModel.n_in;

    fprintf('\n--- MODEL DIMENSIONS ---\n');
    fprintf('ROM.n_modal         : %d\n', ROM.n_modal);
    fprintf('FullModel.n_orig    : %d\n', FullModel.n_orig);
    fprintf('FullModel.n_in      : %d\n', FullModel.n_in);
    fprintf('NumModalStates      : %d\n', NumModalStates);
    fprintf('NumPhysicalStates   : %d\n', NumPhysicalStates);

    %% --- Print Trim Inputs ---
    fprintf('\n--- TRIM INPUTS ---\n');
    fprintf('u_trim = [');
    fprintf(' %.8g', u_trim);
    fprintf(' ]\n');

    %% --- Write Python Configuration JSON ---
    aswing_case_folder_python = path_for_python_server(aswing_case_folder);

    config_data = struct( ...
        'T_sim', T_sim, ...
        'Dt_asw', Dt_asw, ...
        'ASW_FILE', ASW_FILE, ...
        'PNT_FILE', PNT_FILE, ...
        'SET_FILE', SET_FILE, ...
        'STATE_FILE', STATE_FILE, ...
        'GUST_FILE', GUST_FILE, ...
        'ASWING_ALIAS', alias_aswing, ...
        'ASWING_CASE_DIR', aswing_case_folder_python ...
    );

    fid = fopen(json_path, 'w');
    if fid < 0
        error('Unable to open sim_config.json for writing: %s', json_path);
    end

    fprintf(fid, '%s', jsonencode(config_data));
    fclose(fid);

    fprintf('\n[WingLoop] Configuration written to:\n%s\n', json_path);

    %% --- Load Simulink Model ---
    model_path = fullfile(simulink_case_path, model_file);
    try
        load_system(model_path);
    catch ME
        folder_listing = list_folder_for_error(simulink_case_path);
        error(['Unable to load Simulink model file:\n%s\n\n' ...
            'Folder contents:\n%s\n\nOriginal MATLAB error:\n%s'], ...
            model_path, folder_listing, ME.message);
    end
    model_name = resolve_loaded_model_name(model_name, model_path);
    set_param(model_name, 'InitFcn', 'WL_init_callback');

    %% --- Configure AswingPlant Block ---
    aswing_block_path = [model_name '/Non-Linear Plant (WingLoop)/MATLAB System1'];

    set_param(aswing_block_path, 'NumModalStates', num2str(NumModalStates));
    set_param(aswing_block_path, 'NumPhysicalStates', num2str(NumPhysicalStates));

    fprintf('\n[WingLoop] AswingPlant block configured:\n');
    fprintf('Block path        : %s\n', aswing_block_path);
    fprintf('NumModalStates    : %d\n', NumModalStates);
    fprintf('NumPhysicalStates : %d\n', NumPhysicalStates);

    %% --- Configure Simulink Solver ---
    set_param(model_name, 'FixedStep', num2str(Dt_sim));

    fprintf('\n[WingLoop] Simulink model configured:\n');
    fprintf('Model name : %s\n', model_name);
    fprintf('Model file : %s\n', model_path);
    fprintf('Fixed step : %g s\n', Dt_sim);

    fprintf('\n==================================================\n');
    fprintf('Setup complete. Starting Simulink simulation...\n');
    fprintf('==================================================\n\n');
end


function path_out = path_for_python_server(path_in)
    path_out = char(path_in);

    if ~ispc
        return;
    end

    path_slash = strrep(path_out, '\', '/');

    token = regexp(path_slash, '^//wsl\.localhost/[^/]+(/.*)$', ...
        'tokens', 'once');
    if isempty(token)
        token = regexp(path_slash, '^//wsl\$/[^/]+(/.*)$', ...
            'tokens', 'once');
    end

    if ~isempty(token)
        path_out = token{1};
    end
end


function folder_listing = list_folder_for_error(folder_path)
    entries = dir(folder_path);
    if isempty(entries)
        folder_listing = '<folder not found or not readable>';
        return;
    end

    names = string({entries.name});
    names = names(names ~= "." & names ~= "..");
    if isempty(names)
        folder_listing = '<empty folder>';
    else
        folder_listing = strjoin(names, newline);
    end
end


function model_name = resolve_loaded_model_name(requested_model_name, model_path)
    [~, file_model_name] = fileparts(model_path);

    if bdIsLoaded(file_model_name)
        model_name = file_model_name;
        return;
    end

    if bdIsLoaded(requested_model_name)
        model_name = requested_model_name;
        return;
    end

    loaded_models = find_system('SearchDepth', 0, 'type', 'block_diagram');
    loaded_names = strjoin(string(loaded_models), ', ');
    error(['Unable to identify the loaded Simulink model for file: %s\n' ...
        'Loaded block diagrams: %s'], model_path, loaded_names);
end


function value = normalize_text_setting(value, default_value)
    if nargin < 1 || isempty(value)
        value = default_value;
    end

    value = strtrim(string(value));
    if strlength(value) == 0
        value = default_value;
    end

    value = char(value);
end


function aswing_case_folder = resolve_aswing_case_folder( ...
    path_setting, simulink_case_path, wingloop_library_path)

    path_setting = strtrim(string(path_setting));
    if strlength(path_setting) > 0
        aswing_case_folder = char(path_setting);
        return;
    end

    local_case_folder = fullfile(fileparts(simulink_case_path), 'aswing_geometry');
    if exist(local_case_folder, 'dir') == 7
        aswing_case_folder = local_case_folder;
        return;
    end

    default_case_folder = fullfile( ...
        wingloop_library_path, 'wingloop_testrun', 'aswing_geometry');
    if exist(default_case_folder, 'dir') == 7
        aswing_case_folder = default_case_folder;
        return;
    end

    error(['Unable to locate the ASWING case folder. Set ' ...
        'aswing_case_folder in WingLoop_Simulink_Testrun.m.']);
end
