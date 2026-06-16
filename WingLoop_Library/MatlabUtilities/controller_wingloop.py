import json
import os
import shutil
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from WingLoop_Library import WingLoop
from WingLoop_Library.ASW_Helpers import (
    Generate_Analysis_Videos,
    VideoPlot_Generate_postscript_file,
)


def ask_yes_no(prompt, default=False):
    """Ask a yes/no question from the terminal."""
    answer = input(prompt).strip().lower()

    if not answer:
        return default

    return answer in {"y", "yes", "s", "si"}


def normalize_wsl_path(path_value):
    """Convert Windows WSL UNC paths to Linux paths when running in WSL."""
    if not path_value:
        return path_value

    path_text = str(path_value).strip()
    path_slash = path_text.replace("\\", "/")

    prefixes = ("//wsl.localhost/", "//wsl$/")
    for prefix in prefixes:
        if path_slash.lower().startswith(prefix):
            parts = path_slash.split("/", 4)
            if len(parts) >= 5:
                return "/" + parts[4]

    return path_text


def main():
    start_time_total = time.time()

    # ---------------------------------------------------------------------
    # Simulation parameters
    # ---------------------------------------------------------------------
    # Defaults used when sim_config.json is not present.
    Dt = 0.1
    T_sim = 100.0

    ASW_FILE_NAME = "t_tail_HALE.asw"
    PNT_FILE = "t_tail_HALE.pnt"
    SET_FILE = "t_tail_HALE.set"
    STATE_FILE = "t_tail_HALE.state"
    GUST_FILE = "gust_H40.gust"

    ASWING_ALIAS = "aswing"
    ASWING_CASE_DIR = None

    config_path = os.environ.get("WINGLOOP_SIM_CONFIG")
    if not config_path:
        candidate_paths = [
            os.path.join(os.getcwd(), "config", "sim_config.json"),
            os.path.join(os.getcwd(), "sim_config.json"),
        ]
        config_path = next((p for p in candidate_paths if os.path.exists(p)), None)

    # MATLAB/Simulink can write this file before launching Python.
    # If present, it overrides the default parameters above.
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

            Dt = config.get("Dt_asw", Dt)
            T_sim = config.get("T_sim", T_sim)

            ASW_FILE_NAME = config.get("ASW_FILE", ASW_FILE_NAME)
            PNT_FILE = config.get("PNT_FILE", PNT_FILE)
            SET_FILE = config.get("SET_FILE", SET_FILE)
            STATE_FILE = config.get("STATE_FILE", STATE_FILE)
            GUST_FILE = config.get("GUST_FILE", GUST_FILE)
            ASWING_ALIAS = config.get("ASWING_ALIAS", ASWING_ALIAS)
            ASWING_CASE_DIR = normalize_wsl_path(
                config.get("ASWING_CASE_DIR", ASWING_CASE_DIR)
            )

            print(f"[WingLoop] Parameters loaded from {config_path}: T_sim={T_sim}s | Dt={Dt}s")
            print("[WingLoop] ASWING case loaded from configuration:")
            print(f"  ASW_FILE   = {ASW_FILE_NAME}")
            print(f"  PNT_FILE   = {PNT_FILE}")
            print(f"  SET_FILE   = {SET_FILE}")
            print(f"  STATE_FILE = {STATE_FILE}")
            print(f"  GUST_FILE  = {GUST_FILE}")
            print(f"  ASWING_ALIAS = {ASWING_ALIAS}")
            print(f"  ASWING_CASE_DIR = {ASWING_CASE_DIR}")

    K = 1
    N = int(T_sim / Dt) + 2

    # ---------------------------------------------------------------------
    # User options
    # ---------------------------------------------------------------------
    print("\n" + "=" * 50)
    include_gust = ask_yes_no(f"Include the gust file ({GUST_FILE})? (y/n): ", default=False)

    if include_gust:
        print("[WingLoop] Gust enabled.")
    else:
        print("[WingLoop] Gust disabled.")

    print("\n" + "=" * 50)
    generate_video = ask_yes_no("Generate a video after the simulation? (y/n): ", default=False)

    video_format = "gif"
    video_quality = "medium"

    if generate_video:
        video_format = input("Video format (gif/mp4/webp) [default: gif]: ").strip().lower()
        if video_format not in {"gif", "mp4", "webp"}:
            video_format = "gif"

        video_quality = input("Quality (low/medium/high) [default: medium]: ").strip().lower()
        if video_quality not in {"low", "medium", "high"}:
            video_quality = "medium"

        print(f"[Video] Output format: {video_format} | quality: {video_quality}")

    # ---------------------------------------------------------------------
    # Simulink controller setup
    # ---------------------------------------------------------------------
    # This script is intentionally Simulink-only.
    # Bridge_Simulink.py opens the TCP server used by AswingPlant.m.
    control_dir = os.path.dirname(__file__)
    control_filename = "Bridge_Simulink.py"

    # No precomputed controller data is required for the generic Simulink bridge.
    # If a user needs controller-specific data, it should be loaded inside the
    # Simulink model or inside their own controller code, not hardcoded here.
    precomputed_data_path = None

    print("\n" + "=" * 50)
    print("[WingLoop] Simulink bridge mode.")
    print("[WingLoop] Start the Simulink model when the TCP bridge asks for a connection.")

    wingloop = WingLoop()

    wingloop.Launch_WingLoop_Control(
        cntrl_directory=control_dir,
        cntrl_filename=control_filename,
        timestep=Dt,
        precomputed_filename=precomputed_data_path,
        rebuild_fmu_file=True,
        show_simulink_window=True,
    )

    print(f"[WingLoop] Simulation configured for N = {N} iterations.")

    # Plotting is disabled by default for the Simulink workflow to reduce overhead.
    wingloop.InitializePlot(
        liveplot=False,
        plot_variables=["earth X", "earth Y", "earth Z", "Heading", "Elev.", "Bank"],
        plot_sim_time=N * Dt,
        plot_refreshtime=1,
        plot_size=(16, 10),
        N_steps=N,
    )

    # ---------------------------------------------------------------------
    # ASWING case setup
    # ---------------------------------------------------------------------
    library_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    if ASWING_CASE_DIR:
        aswing_working_dir = os.path.abspath(ASWING_CASE_DIR)
    else:
        aswing_working_dir = os.path.join(
            library_dir, "wingloop_testrun", "aswing_geometry"
        )
    geometry_dir = aswing_working_dir

    # Absolute path used by Python for checks and optional video generation.
    aswing_geometry_file_abs = os.path.join(geometry_dir, ASW_FILE_NAME)

    # Short relative path passed to ASWING.
    # Aswing_Director changes directory to aswing_working_dir before launching ASWING,
    # so this avoids long absolute paths and remains portable across cloned repos.
    aswing_geometry_file = os.path.relpath(
        aswing_geometry_file_abs,
        start=aswing_working_dir,
    )

    point_file = PNT_FILE
    settings_file = SET_FILE
    state_file = STATE_FILE
    gust_file = GUST_FILE

    print("[WingLoop] ASWING working directory:", aswing_working_dir)
    print("[WingLoop] ASWING geometry absolute path:", aswing_geometry_file_abs)
    print("[WingLoop] ASWING geometry path passed to ASWING:", aswing_geometry_file)

    if not os.path.isdir(aswing_working_dir):
        raise FileNotFoundError(f"ASWING working directory not found: {aswing_working_dir}")

    if not os.path.isfile(aswing_geometry_file_abs):
        raise FileNotFoundError(f"ASWING geometry file not found: {aswing_geometry_file_abs}")

    for required_file in [point_file, settings_file, state_file]:
        required_path = os.path.join(aswing_working_dir, required_file)
        if not os.path.isfile(required_path):
            raise FileNotFoundError(f"Required ASWING file not found: {required_path}")

    if include_gust:
        gust_path = os.path.join(aswing_working_dir, gust_file)
        if not os.path.isfile(gust_path):
            raise FileNotFoundError(f"Gust file requested but not found: {gust_path}")

    wingloop.Launch_ASWING(
        aswing_fullpath=None,
        aswing_alias=ASWING_ALIAS,
        sim_directory=aswing_working_dir,
        asw_filename=aswing_geometry_file,
        print_output=False,
        timer_text=0.03,
        finished_writing_check_timestep=0.001,
    )

    wingloop.Deactivate_Graphics()
    wingloop.Load_Files(point_file)
    wingloop.Load_Files(settings_file)
    wingloop.Load_Files(state_file)

    if include_gust:
        wingloop.Load_Files(gust_file)

    # ---------------------------------------------------------------------
    # Run simulation
    # ---------------------------------------------------------------------
    print("\n[WingLoop] Starting transient simulation...")
    start_time_sim = time.time()

    wingloop.Time_Transient_Simulation(Dt, N, K)

    end_time_sim = time.time()
    print(f"[WingLoop] Simulation time: {end_time_sim - start_time_sim:.2f} s")

    # ---------------------------------------------------------------------
    # Save results
    # ---------------------------------------------------------------------
    result_name = "sim_results"

    wingloop.Outputting_The_State_File(statefile_filename=result_name)
    wingloop.Outputting_The_Results(custom_filename=result_name)
    wingloop.Closing_WingLoop(removefiles=False)

    print("\n[WingLoop] Simulation completed successfully.")

    # ---------------------------------------------------------------------
    # Optional video generation
    # ---------------------------------------------------------------------
    if generate_video:
        print("\n" + "=" * 50)
        print("[Video] Starting video generation...")

        try:
            shutil.copy2(aswing_geometry_file_abs, aswing_working_dir)
            print(f"[Video] Geometry copied to ASWING working directory: {os.path.basename(aswing_geometry_file_abs)}")
        except Exception as exc:
            print(f"[Video] Warning: unable to copy geometry file: {exc}")

        old_plot = os.path.join(aswing_working_dir, "plot.ps")
        if os.path.exists(old_plot):
            try:
                os.remove(old_plot)
                print("[Video] Removed previous plot.ps.")
            except Exception:
                pass

        results_state_file = result_name + ".state"

        try:
            ps_path = VideoPlot_Generate_postscript_file(
                geometry_filename=os.path.basename(aswing_geometry_file_abs),
                reference_folder=aswing_working_dir,
                input_files=[results_state_file],
                video_folder=os.path.join(aswing_working_dir, "videos"),
                aswing_alias=ASWING_ALIAS,
                stable_duration=4.0,
                poll_interval=1.0,
                timeout=300,
            )

            print(f"[Video] PostScript generated: {ps_path}")

            out_path = Generate_Analysis_Videos(
                ps_path,
                Dt=Dt,
                videofile=video_format,
                transpose=1,
                quality=video_quality,
                keep_frames=False,
            )

            print(f"[Video] Video saved: {out_path}")

        except Exception as exc:
            print(f"[Video] Error during video generation: {exc}")
            print("[Video] Make sure ghostscript and ffmpeg are installed:")
            print("        sudo apt install ghostscript ffmpeg")

    print(f"\n[WingLoop] Total elapsed time: {time.time() - start_time_total:.2f} s")


if __name__ == "__main__":
    main()
