clc;
close all;
clear;

%% ========================================================================
%  USER CONFIGURATION
%  Change only this section when using a different aircraft, trim point,
%  simulation setup, conda environment, or ASWING alias.
%  ========================================================================

%% --- WingLoop Library Path ---
% Leave empty when this folder is inside the WingLoop repository.
% If you copy this Simulink test folder elsewhere, set this to the absolute
% path of WingLoop/WingLoop_Library on your machine.
wingloop_library_path = "";

%% --- Python / Conda Environment ---
% Put here the conda environment used to run controller_wingloop.py.
% Leave empty to use the default environment name: WINGLOOP.
wingloop_env = "WINGLOOP";

%% --- ASWING Executable Alias ---
% Put here the ASWING command/alias used on this machine.
% Leave empty to use the default alias: aswing.
alias_aswing = "aswing";

%% --- ASWING Case Folder ---
% Leave empty to use ../aswing_geometry if it exists, otherwise the default
% WingLoop_Library/wingloop_testrun/aswing_geometry folder.
aswing_case_folder = "";

%% --- Time Configuration ---
T_sim      = 10;     % Total simulation time [s]
Dt_asw     = 0.1;    % ASWING step size [s]
Dt_sim     = 0.1;    % Simulink solver step size [s]
Ts_control = 0.1;    % Controller sample time [s]
tau        = 0.1;    % Filter time constant
t_int      = 0.5;    % Integral time constant / user-defined parameter

%% --- ASWING Case Files ---
% These files must be located in the selected aswing_case_folder.
ASW_FILE   = 't_tail_HALE.asw';
PNT_FILE   = 't_tail_HALE.pnt';
SET_FILE   = 't_tail_HALE.set';
STATE_FILE = 't_tail_HALE.state';
GUST_FILE  = 'gust_H40.gust';

%% --- Aircraft / Model Dimensions ---
% Change these values when using a different aircraft model.
ROM.n_modal      = 91;    % Number of modal states
FullModel.n_orig = 1882;  % Number of original physical states
FullModel.n_in   = 6;     % Number of control inputs

%% --- Trim Control Inputs ---
% Change these values when using a different trim point.
F2ref = -6.63806152;
F3ref = 4.54747351E-12;
E2ref = 23.6475887;

u_trim = [0, F2ref, F3ref, 0, E2ref, E2ref];

%% --- Simulink Model ---
model_name = 'WingLoop_Controller';
model_file = 'WingLoop_Controller.slx';

%% ========================================================================
%  AUTOMATIC SETUP AND SIMULATION
%  Do not modify this section unless you are changing the WingLoop interface.
%  ========================================================================

simulink_case_path = fileparts(mfilename('fullpath'));
wingloop_library_path = resolve_wingloop_library_path( ...
    wingloop_library_path, simulink_case_path);

matlab_utilities_path = fullfile(wingloop_library_path, 'MatlabUtilities');
if exist(matlab_utilities_path, 'dir') ~= 7
    error('MatlabUtilities folder not found: %s', matlab_utilities_path);
end
addpath(matlab_utilities_path);

model_name = run_wingloop_simulink_setup( ...
    T_sim, Dt_asw, Dt_sim, Ts_control, tau, t_int, ...
    ASW_FILE, PNT_FILE, SET_FILE, STATE_FILE, GUST_FILE, ...
    ROM, FullModel, u_trim, ...
    model_name, model_file, wingloop_env, alias_aswing, ...
    wingloop_library_path, aswing_case_folder, simulink_case_path ...
);

sim(model_name);


function wingloop_library_path = resolve_wingloop_library_path(path_setting, start_path)
    path_setting = strtrim(string(path_setting));
    if strlength(path_setting) > 0
        wingloop_library_path = char(path_setting);
        return;
    end

    probe = start_path;
    while true
        if exist(fullfile(probe, 'WingLoop.py'), 'file') == 2 && ...
                exist(fullfile(probe, 'MatlabUtilities'), 'dir') == 7
            wingloop_library_path = probe;
            return;
        end

        parent = fileparts(probe);
        if strcmp(parent, probe)
            break;
        end
        probe = parent;
    end

    error(['Unable to locate WingLoop_Library automatically. Set ' ...
        'wingloop_library_path in WingLoop_Simulink_Testrun.m.']);
end
