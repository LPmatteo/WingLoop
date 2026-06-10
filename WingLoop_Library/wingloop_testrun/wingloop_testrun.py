import numpy as np
import time
import os
import matlab.engine
from WingLoop_Library import WingLoop
import json
from WingLoop_Library import VideoPlot_Generate_postscript_file, Generate_Analysis_Videos, Generate_Strobe_Plot
import shutil

def main():
    tfirst = time.time()

    # =========================================================================
    # GENERIC CONFIGURATION - AUTOMATIC RELATIVE PATHS
    # =========================================================================
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Path to ASWING Geometry Folder
    ASW_DIR  = os.path.join(BASE_DIR, "aswing_geometry")
    
    # !!! REPLACE THESE WITH YOUR ACTUAL AIRCRAFT FILE NAMES !!!
    ASW_FILE = os.path.join(ASW_DIR, "my_aircraft.asw") 
    PNT_FILE = "my_aircraft.pnt" 
    SET_FILE = "my_aircraft.set" 
    STATE_FILE = "my_aircraft.state" 
    GUST_FILE = "gust_H40.gust" 
    
    # Optional precomputed file path for LQR/Controllers
    PRECOMPUTED_DATA_PATH = os.path.join(BASE_DIR, "simulink_controller", "lqr_data.mat")
    # =========================================================================

    # 1) Default parameters
    Dt = 0.1
    T_sim = 100.0  

    # 2) Automatic reading from MATLAB config file (if exists)
    json_config_path = os.path.join(BASE_DIR, 'sim_config.json')
    if os.path.exists(json_config_path):
        with open(json_config_path, 'r') as f:
            config = json.load(f)
            Dt = config.get('Dt_asw', Dt)
            T_sim = config.get('T_sim', T_sim)
            print(f"[*] Parameters synchronized from MATLAB: T_sim={T_sim}s | Dt={Dt}s")

    K = 1

    print("\n" + "="*50)
    print("SELECT CONTROLLER TYPE:")
    print(" 1 : SIMULINK LQI (TCP Bridge -> AswingPlant.m)")
    print(" 2 : PYTHON (Open Loop / Custom)")
    print(" 3 : MATLAB (UserController.m - Standard)")
    choice = input("Choice (1, 2, 3): ").strip()
    
    # ── Gust Setup ─────────────────────────────────────────
    print("\n" + "="*50)
    want_gust = input(f"Do you want to include the gust file ({GUST_FILE})? (y/n): ").strip().lower()
    include_gust = want_gust in ['y', 'yes']
    if include_gust:
        print("[*] Gust ENABLED.")
    else:
        print("[*] Gust DISABLED.")

    # ── Video Setup ──────────────────────────────────────────────────
    print("\n" + "="*50)
    want_video = input("Do you want to generate a video of the simulation after the run? (y/n): ").strip().lower()
    generate_video = want_video in ['y', 'yes']
    if generate_video:
        video_format = input("Video format (gif/mp4/webp) [default: mp4]: ").strip().lower()
        if video_format not in ['gif', 'mp4', 'webp']: video_format = 'mp4'
        video_quality = input("Quality (low/medium/high) [default: medium]: ").strip().lower()
        if video_quality not in ['low', 'medium', 'high']: video_quality = 'medium'
    # ──────────────────────────────────────────────────────────────────
    eng = None
    percorso_dati = None

    if choice == "1":
        selector = "sim"
        control_dir = os.path.join(BASE_DIR, "simulink_controller")
        control_filename = "Bridge_Simulink.py"
        percorso_dati = PRECOMPUTED_DATA_PATH
        print(f"[*] BRIDGE mode (Simulink).")

    elif choice == "2":
        selector = "py"
        control_dir = os.path.join(BASE_DIR, "python_controller")
        control_filename = "Unified_OL.py"
        percorso_dati = None
        print("[*] Open Loop / Python Custom mode.")

    elif choice == "3":
        selector = "mat"
        control_dir = os.path.join(BASE_DIR, "matlab_controller")
        control_filename = "UserController.m"
        percorso_dati = PRECOMPUTED_DATA_PATH
        print("[*] Connecting to MATLAB...")
        try:
            names = matlab.engine.find_matlab()
            if names: eng = matlab.engine.connect_matlab(names[0])
            else: eng = matlab.engine.start_matlab()
        except Exception as e:
            print(f"[-] MATLAB Error: {e}")
            return

    WL_Instance = WingLoop()

    # Launch controller
    WL_Instance.Launch_WingLoop_Control(
        cntrl_directory = control_dir,
        cntrl_filename = control_filename,
        timestep = Dt,
        precomputed_filename = percorso_dati,
        rebuild_fmu_file = True,
        show_simulink_window = True
    )

    if choice == "1":
        N = int(T_sim / Dt) + 2
    else:
        if 'WINGLOOP_N' in os.environ: N = int(os.environ['WINGLOOP_N'])
        else: N = int(T_sim / Dt)

    print(f"[*] Setting simulation environment for N = {N} iterations.")

    # Initialize plot
    WL_Instance.InitializePlot(
        liveplot = (choice == "2"), 
        plot_variables = ["earth X", "earth Y", "earth Z", "Heading", "Elev.", "Bank"],
        plot_sim_time = N * Dt,
        plot_refreshtime = 1,
        plot_size = (16, 10),
        N_steps = N
    )

    WL_Instance.Launch_ASWING(
        aswing_fullpath = None,
        aswing_alias = "aswing",
        sim_directory = ASW_DIR, 
        asw_filename = ASW_FILE,
        print_output = False, 
        timer_text = 0.0001,
        finished_writing_check_timestep = 0.01
    )

    WL_Instance.Deactivate_Graphics()
    
    # Load available files
    for f in [PNT_FILE, SET_FILE, STATE_FILE]:
        try: WL_Instance.Load_Files(f)
        except Exception as e: print(f"[-] Unable to load {f}: {e}")
            
    if include_gust:
        try: WL_Instance.Load_Files(GUST_FILE)
        except Exception as e: print(f"[-] Unable to load {GUST_FILE}: {e}")

    print(f"\n[*] Starting Transient simulation...")
    tstart = time.time()
    WL_Instance.Time_Transient_Simulation(Dt, N, K)
    tend = time.time()
    print(f"[wingloop_testrun] simulation time: {tend - tstart:.2f} s")

    result_name = "sim_latest_results"

    WL_Instance.Outputting_The_State_File(statefile_filename=result_name)
    WL_Instance.Outputting_The_Results(custom_filename=result_name)
    WL_Instance.Closing_WingLoop(removefiles = False)

    print("\n[+] Operation completed successfully.")

    # ── Video Generation ───────────────────────────
    if generate_video:
        print("\n" + "="*50)
        print("[VIDEO] Starting video generation...")
        try: shutil.copy2(ASW_FILE, ASW_DIR)
        except: pass

        vecchio_plot = os.path.join(ASW_DIR, "plot.ps")
        if os.path.exists(vecchio_plot):
            try: os.remove(vecchio_plot)
            except: pass

        results_state_file = result_name + ".state"

        try:
            ps_path = VideoPlot_Generate_postscript_file(
                geometry_filename=os.path.basename(ASW_FILE),
                reference_folder=ASW_DIR,
                input_files=[results_state_file],
                video_folder=os.path.join(ASW_DIR, "videos"),
                aswing_alias="aswing",
                stable_duration=4.0,  
                poll_interval=1.0,    
                timeout=300           
            )

            out_path = Generate_Analysis_Videos(
                ps_path, Dt=Dt, videofile=video_format, transpose=1,        
                quality=video_quality, keep_frames=False
            )
            print(f"[VIDEO] ✓ Video saved: {out_path}")

        except Exception as e:
            print(f"[VIDEO] Error during video generation: {e}")

if __name__ == "__main__":
    main()