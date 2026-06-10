## WingLoop 3.0
<div align="center">
  <img src="./docs/wingLoop_image.jpg" alt="WingLoop GUI during a simulation run" width="100%" />
</div>

**Author:** Matteo Alfoso Incarbone
**Contact:** lpmatteo241@gmail.com  
**Last Modified:** 10/06/26  
**Platform:** Windows wsl  
**Tested with:** ASWING 5.98  


**WingLoop** is a Python-based framework that enables closed-loop aeroservoelastic simulations in ASWING using external controllers developed in **Python**, **MATLAB**, or **Simulink**.

The library acts as a communication layer between ASWING and external control environments, allowing users to implement custom control laws while retaining ASWING as the high-fidelity aeroservoelastic plant.

---

## Architecture

```text
ASWING
   │
   ▼
WingLoop
   │
   ├── Python Controller
   ├── MATLAB Controller
   └── Simulink Controller
```

WingLoop automatically:

* Launches and manages ASWING
* Exchanges aircraft states and control commands
* Executes user-defined control laws
* Records simulation data
* Generates plots and simulation outputs
* Supports post-processing and video generation

---

## Repository Structure

```text
WingLoop/
│
├── WingLoop_Library/
│
├── wingloop_testrun/
│   │
│   ├── aswing_geometry/
│   │
│   ├── python_controller/
│   │
│   ├── matlab_controller/
│   │
│   ├── simulink_controller/
│   │   ├── WL_main_simulink.slx
│   │   ├── AswingPlant.m
│   │   └── Bridge_Simulink.py
│   │
│   └── wingloop_testrun.py
│
├── requirements.txt
└── README.md
```

---

## Requirements

The following software must be installed:

* Python 3.10+
* ASWING
* NumPy
* Matplotlib

Optional:

* MATLAB
* Simulink
* MATLAB Engine for Python

Install Python dependencies using:

```bash
pip install -r requirements.txt
```

---

## ASWING Geometry Folder

The folder:

```text
wingloop_testrun/aswing_geometry/
```

contains all files required to initialize an ASWING simulation.

Typical contents include:

```text
.aircraft.asw
.aircraft.state
.aircraft.pnt
.aircraft.set
.optional.gust
```

These files define:

* Aircraft geometry
* Initial trim condition
* Simulation settings
* Plot settings
* Optional gust disturbances

Replace the example files with those corresponding to your own aircraft model.

---

## Running a Simulation

Open:

```text
wingloop_testrun/wingloop_testrun.py
```

and update the filenames inside the configuration section:

```python
ASW_FILE
PNT_FILE
SET_FILE
STATE_FILE
GUST_FILE
```

to match your aircraft files.

Launch the simulation:

```bash
python wingloop_testrun.py
```

WingLoop will ask which controller environment should be used:

```text
1 : Simulink
2 : Python
3 : MATLAB
```

Select the desired option and start the simulation.

---

## Python Controllers

Custom Python controllers can be placed inside:

```text
python_controller/
```

WingLoop automatically loads the selected controller and executes it during the simulation.

The controller receives:

```python
instantaneous_state
Dt
```

and returns a dictionary containing the desired control commands.

Example:

```python
return {
    "F1": 0.0,
    "F2": 0.0,
    "E1": 0.0
}
```

---

## MATLAB Controllers

Custom MATLAB controllers can be placed inside:

```text
matlab_controller/
```

WingLoop automatically establishes communication with MATLAB and executes the selected controller at each simulation step.

---

## Simulink Interface

The repository includes a reference Simulink implementation:

```text
WL_main_simulink.slx
```

The model demonstrates:

* TCP communication between Simulink and WingLoop
* Use of the AswingPlant System Block
* Exchange of aircraft states and control inputs
* Open-loop simulation execution

Users can replace the open-loop command source with their own control architecture.

---

## AswingPlant Block

The Simulink interface is based on the custom MATLAB System Block:

```text
AswingPlant.m
```

which communicates with WingLoop through a TCP bridge.

Configurable parameters include:

```text
ServerHost
ServerPort
NumModalStates
NumPhysicalStates
```

### Modal States

The parameter:

```text
NumModalStates
```

can be modified when implementing Reduced Order Models (ROMs) or custom modal-state representations.

For standard simulations the default value may be left unchanged.

---

## Simulation Outputs

At the end of each run WingLoop can generate:

* JSON simulation logs
* State files
* PDF plots
* Animation videos

Supported video formats:

```text
mp4
gif
webp
```

---

## Post-Processing

WingLoop includes utilities for:

* Simulation visualization
* Strobe plots
* Animation generation
* Post-processing of ASWING results

Generated files are stored inside the simulation directory.

---

## Notes

WingLoop assumes that:

* The aircraft trim condition has already been generated in ASWING
* A valid `.state` file is available
* ASWING can be launched from the command line

The framework does not generate trim points automatically.

---

## Acknowledgements

WingLoop was developed to facilitate aeroservoelastic control studies using ASWING and modern control-design environments such as Python, MATLAB, and Simulink.
