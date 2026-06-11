clc; close all;
clear all


%% --- Time Configuration ---
T_sim      = 10;    % Total simulation time [s]
Dt_asw     = 0.1;    % ASWING step size [s]
Dt_sim     = 0.1;    % Simulink solver step size [s]
Ts_control = 0.1;    % Controller sample time [s]
tau        = 0.1;    % Filter time constant
t_int      = 0.5;    

fprintf('\n--- TIME CONFIGURATION ---\n');
fprintf('T_sim: %g s | Dt_ASWING: %g s | Ts_Control: %g s\n', T_sim, Dt_asw, Ts_control);

% Python interface setup
python_path = '/home/lpmatteo/software/WingLoop/WingLoop_Library/wingloop_testrun/';
json_path   = fullfile(python_path, 'sim_config.json');
config_data = struct('T_sim', T_sim, 'Dt_asw', Dt_asw);

fid = fopen(json_path, 'w');
fprintf(fid, '%s', jsonencode(config_data));
fclose(fid);

% Paths
addpath('/home/lpmatteo/software/WingLoop/WingLoop_Library/wingloop_testrun/simulink_controller/');

%% Block parameters : change depending on geometry used


ROM.n_modal = 92 ;  %only if ROM is included
FullModel.n_orig = 1882 ;   %Geometry
FullModel.n_in = 6 ;  %Geometry


% Change depending on trimming point used
F2ref = -6.63806152; 
F3ref = 4.54747351E-12; 
E2ref = 23.6475887;
u_trim = [0, F2ref, F3ref, 0, E2ref, E2ref]; 

sim('WL_test.slx')