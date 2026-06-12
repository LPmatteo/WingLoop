# WingLoop 3.0

<div align="center">
  <img src="./docs/wingLoop_image.jpg" alt="WingLoop during a simulation run" width="100%" />
</div>

**Author:** Matteo Alfonso Incarbone  
**Contact:** lpmatteo241@gmail.com  
**Platform:** Windows + WSL  
**Tested with:** ASWING 5.98  

---

## Overview

WingLoop is a Python-based interface for running aeroservoelastic simulations in **ASWING** with external control commands provided by **Simulink**.

This repository contains a **Simulink-only implementation** of WingLoop.

The workflow is:

```text
Simulink
   │
   ▼
AswingPlant.m
   │
   ▼
TCP Bridge
   │
   ▼
WingLoop
   │
   ▼
ASWING
```

Control laws are expected to be implemented directly inside the Simulink model.

Python and MATLAB controller workflows available in previous WingLoop versions are not part of this implementation.

---

## Main Features

WingLoop provides:

- ASWING process management
- TCP communication between Simulink and Python
- Exchange of ASWING states and Simulink control inputs
- Open-loop and closed-loop Simulink simulations
- ASWING state and JSON result export
- Optional plot and video generation tools

---

## Repository Structure

```text
WingLoop/
│
├── README.md
│
└── WingLoop_Library/
    │
    ├── WingLoop.py
    ├── Aswing_Director.py
    ├── PyControl.py
    ├── PyControl_IO.py
    ├── PyControl_Plot.py
    ├── ASW_Helpers.py
    ├── __init__.py
    │
    ├── test_files/
    │
    └── wingloop_testrun/
        │
        ├── controller_wingloop.py
        ├── sim_config.json
        ├── python_inputs.txt
        │
        ├── Geometries/
        │   └── t_tail_HALE.asw
        │
        ├── aswing_geometry/
        │   ├── t_tail_HALE.pnt
        │   ├── t_tail_HALE.set
        │   ├── t_tail_HALE.state
        │   └── gust_H40.gust
        │
        └── simulink_controller/
            ├── WL_main.m
            ├── WL_main_simulink.slx
            ├── AswingPlant.m
            └── Bridge_Simulink.py
```

Generated files such as `input`, `output`, `sim_results.*`, `slprj/`, `__pycache__/`, and `.slxc` files should not be committed to the repository.

---

## Requirements

The following software is required:

- Windows with WSL
- Python 3.10+
- ASWING
- MATLAB
- Simulink
- NumPy
- Matplotlib

Optional tools for video generation:

- Ghostscript
- FFmpeg

Install Python dependencies with:

```bash
pip install -r requirements.txt
```

If Ghostscript and FFmpeg are needed:

```bash
sudo apt install ghostscript ffmpeg
```

---

## ASWING Command Alias

WingLoop expects ASWING to be launchable from the WSL terminal.

For example, the command:

```bash
aswing
```

should start ASWING.

If needed, define an alias in your shell configuration file, for example:

```bash
alias aswing='/path/to/aswing'
```

Then reload the shell:

```bash
source ~/.bashrc
```

---

## Running the Simulink Example

Open MATLAB and run the user-facing main script:

```matlab
WL_main
```

from:

```text
WingLoop/WingLoop_Library/wingloop_testrun/simulink_controller/
```

`WL_main.m` is the main entry point of the workflow. It configures the simulation parameters, selects the ASWING files, sets the model dimensions and trim inputs, writes `sim_config.json`, configures `AswingPlant.m`, and starts the Simulink simulation.

When the model is ready, press **Run** in Simulink.

The Simulink model automatically launches the Python WingLoop server through WSL. The Python server starts ASWING and exchanges data with the `AswingPlant.m` block through TCP.

---

## Simulink Interface

The Simulink interface is based on:

```text
WingLoop/WingLoop_Library/wingloop_testrun/simulink_controller/AswingPlant.m
```

`AswingPlant.m` is a MATLAB System block that communicates with Python through TCP.

The Python-side TCP bridge is:

```text
WingLoop/WingLoop_Library/wingloop_testrun/simulink_controller/Bridge_Simulink.py
```

The user-facing main script is:

```text
WingLoop/WingLoop_Library/wingloop_testrun/simulink_controller/WL_main.m
```

This is the file where the user sets the simulation time, ASWING case files, model dimensions, trim inputs, and Simulink model name.

The Python script:

```text
WingLoop/WingLoop_Library/wingloop_testrun/controller_wingloop.py
```

is launched automatically by the Simulink workflow through WSL and should normally not be edited by the user.

---

## Changing the Aircraft Model

WingLoop does not automatically generate aircraft trim conditions, reduced-order models, or ASWING initialization files.

To use a different aircraft, the user must manually provide the corresponding ASWING files and update the aircraft-specific parameters used by the Simulink model.

### Step 1 — Place the ASWING Geometry File

Place the aircraft geometry file:

```text
aircraft.asw
```

inside:

```text
WingLoop/WingLoop_Library/wingloop_testrun/Geometries/
```

For the provided example:

```text
WingLoop/WingLoop_Library/wingloop_testrun/Geometries/t_tail_HALE.asw
```

Only the `.asw` geometry file should be placed in `Geometries/`.

### Step 2 — Place the ASWING Initialization Files

Place the three ASWING initialization files:

```text
aircraft.pnt
aircraft.set
aircraft.state
```

inside:

```text
WingLoop/WingLoop_Library/wingloop_testrun/aswing_geometry/
```

For the provided example:

```text
WingLoop/WingLoop_Library/wingloop_testrun/aswing_geometry/t_tail_HALE.pnt
WingLoop/WingLoop_Library/wingloop_testrun/aswing_geometry/t_tail_HALE.set
WingLoop/WingLoop_Library/wingloop_testrun/aswing_geometry/t_tail_HALE.state
```

Optional gust files should also be placed inside:

```text
WingLoop/WingLoop_Library/wingloop_testrun/aswing_geometry/
```

For example:

```text
WingLoop/WingLoop_Library/wingloop_testrun/aswing_geometry/gust_H40.gust
```

### Step 3 — Select the Files in the MATLAB Main Script

Open the user-facing main script:

```text
WingLoop/WingLoop_Library/wingloop_testrun/simulink_controller/WL_main.m
```

and select the ASWING files to be used by the simulation:

```matlab
ASW_FILE = 't_tail_HALE.asw';

PNT_FILE   = 't_tail_HALE.pnt';
SET_FILE   = 't_tail_HALE.set';
STATE_FILE = 't_tail_HALE.state';
GUST_FILE  = 'gust_H40.gust';
```

These file names are written automatically to `sim_config.json`, which is then read by `controller_wingloop.py`.

The Python launcher should not be modified when changing aircraft.

### Step 4 — Update the Aircraft Dimensions

In the same MATLAB main script, update the aircraft-dependent dimensions:

```matlab
ROM.n_modal      = 91;    % Number of modal states, if a ROM is used

FullModel.n_orig = 1882;  % Number of original physical states
FullModel.n_in   = 6;     % Number of control inputs
```

These values depend on the selected aircraft geometry and on the state/input definition used by the Simulink model.

The dimensions used by `AswingPlant.m` are computed automatically from:

```matlab
NumModalStates    = ROM.n_modal;
NumPhysicalStates = FullModel.n_orig + FullModel.n_in;
```

Therefore, `NumModalStates` and `NumPhysicalStates` should not be edited manually inside `AswingPlant.m`.

### Step 5 — Update the Trim Inputs

The trim input vector must match the trimming point contained in the selected `.state` file.

For the provided example:

```matlab
F2ref = -6.63806152;
F3ref = 4.54747351E-12;
E2ref = 23.6475887;

u_trim = [ ...
    0, ...
    F2ref, ...
    F3ref, ...
    0, ...
    E2ref, ...
    E2ref ...
];
```

When using a different trim point, the user must update `F2ref`, `F3ref`, `E2ref`, and `u_trim` accordingly.

The order of `u_trim` must be consistent with the control-input order expected by the Simulink model and by the WingLoop TCP bridge.

---

## ASWING File Path Logic

The Python launcher uses two different folders:

```text
Geometries/
```

for the `.asw` geometry file, and:

```text
aswing_geometry/
```

for the `.pnt`, `.set`, `.state`, gust files, and simulation outputs.

This separation avoids long absolute paths being passed directly to ASWING. The geometry file is passed to ASWING as a short relative path from the ASWING working directory.

---

## Simulation Outputs

Simulation outputs are written inside:

```text
WingLoop/WingLoop_Library/wingloop_testrun/aswing_geometry/
```

Typical generated files include:

```text
input
output
sim_results.json
sim_results.pdf
sim_results.state
plot.ps
videos/
```

These files are generated automatically and should not be committed to GitHub.

---

## Notes

- The aircraft trim condition must already exist in the `.state` file.
- WingLoop does not generate trim conditions automatically.
- The Simulink model is responsible for defining the control law.
- `AswingPlant.m` must run in interpreted execution mode.
- ASWING must be available from the WSL command line.

---

## Troubleshooting

### Simulink cannot connect to Python

Make sure the Python server is running and listening on port `5005`.

### ASWING does not start

Check that the `aswing` command works from WSL.

### Output files are not generated

Check that:

- `.pnt`, `.set`, and `.state` files are in `aswing_geometry/`
- the `.asw` file is in `Geometries/`
- `Aswing_Director.py` and `WingLoop.py` use the corrected file-write synchronization logic
- ASWING is launched from the correct working directory

---

## Acknowledgements

WingLoop was developed to support aeroservoelastic control studies using ASWING and modern control-design environments such as Simulink.
