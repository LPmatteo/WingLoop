import json
import os
import shutil
import time

from WingLoop_Library import (
    WingLoop,
    VideoPlot_Generate_postscript_file,
    Generate_Analysis_Videos,
)


def ask_yes_no(prompt, default=False):
    """Ask a yes/no question from the terminal."""
    answer = input(prompt).strip().lower()

    if not answer:
        return default

    return answer in {"y", "yes", "s", "si"}


def main():
    start_time_total = time.time()

    # ---------------------------------------------------------------------
    # Simulation parameters
    # ---------------------------------------------------------------------
    # Defaults used when sim_config.json is not present.
    Dt = 0.1
    T_sim = 100.0

    # MATLAB/Simulink can write this file before launching Python.
    # If present, it overrides the default parameters above.
    if os.path.exists("sim_config.json"):
        with open("sim_config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            Dt = config.get("Dt_asw", Dt)
            T_sim = config.get("T_sim", T_sim)
            print(f"[WingLoop] Parameters loaded from sim_config.json: T_sim={T_sim}s | Dt={Dt}s")

    K = 1
    N = int(T_sim / Dt) + 2

    # ---------------------------------------------------------------------
    # User options
    # ---------------------------------------------------------------------
    print("\n" + "=" * 50)
    include_gust = ask_yes_no("Include the gust file (gust_H40.gust)? (y/n): ", default=False)

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
    control_dir = "simulink_controller"
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
    base_dir = os.path.dirname(os.path.abspath(__file__))

    aswing_working_dir = os.path.join(base_dir, "aswing_geometry")
    geometry_dir = os.path.join(base_dir, "Geometries")

    # Absolute path used by Python for checks and optional video generation.
    aswing_geometry_file_abs = os.path.join(geometry_dir, "t_tail_HALE.asw")

    # Short relative path passed to ASWING.
    # Aswing_Director changes directory to aswing_working_dir before launching ASWING,
    # so this avoids long absolute paths and remains portable across cloned repos.
    aswing_geometry_file = os.path.relpath(
        aswing_geometry_file_abs,
        start=aswing_working_dir,
    )

    point_file = "t_tail_HALE.pnt"
    settings_file = "t_tail_HALE.set"
    state_file = "t_tail_HALE.state"
    gust_file = "gust_H40.gust"

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
        aswing_alias="aswing",
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
                aswing_alias="aswing",
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
