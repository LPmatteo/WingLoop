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


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _extract_numeric_series(value):
    if isinstance(value, list):
        series = []
        for item in value:
            if _is_number(item):
                series.append(float(item))
            elif isinstance(item, list):
                nums = [float(x) for x in item if _is_number(x)]
                if nums:
                    series.append(nums[0])
            elif isinstance(item, dict):
                for candidate in ("value", "data", "y", "Y"):
                    if candidate in item and _is_number(item[candidate]):
                        series.append(float(item[candidate]))
                        break
        return series

    if isinstance(value, dict):
        for candidate in ("values", "data", "Value", "Data"):
            if candidate in value:
                return _extract_numeric_series(value[candidate])

    return []


def _find_series(data, names):
    lower_map = {str(k).lower().replace(" ", "").replace("_", ""): k for k in data.keys()}
    for name in names:
        key = lower_map.get(name.lower().replace(" ", "").replace("_", ""))
        if key is not None:
            series = _extract_numeric_series(data[key])
            if series:
                return key, series
    return None, []


def generate_fallback_video_from_json(results_json, output_mp4, Dt, max_frames=600):
    """Create a lightweight MP4 from sim_results.json when ASWING movie export fails."""
    if not os.path.isfile(results_json):
        raise FileNotFoundError(f"Fallback video source not found: {results_json}")

    with open(results_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise RuntimeError("Fallback video expects sim_results.json to contain a JSON object.")

    variables = data.get("ModelVariables", data)
    if not isinstance(variables, dict):
        variables = data

    _, time_series = _find_series(variables, ["Time", "time", "t"])
    _, x = _find_series(variables, ["earth X", "X", "sim_X"])
    _, y = _find_series(variables, ["earth Y", "Y", "sim_Y"])
    _, z = _find_series(variables, ["earth Z", "Z", "sim_Z"])
    vx_name, vx = _find_series(variables, ["Vx", "V_x", "Velocity", "Ux", "sim_Vx"])
    theta_name, theta = _find_series(variables, ["theta", "Elev.", "Pitch", "sim_theta"])

    lengths = [len(s) for s in (x, y, z, vx, theta) if len(s) > 1]
    if not lengths:
        raise RuntimeError("Fallback video could not find numeric time histories in sim_results.json.")

    n = min(lengths)
    stride = max(1, int((n + max_frames - 1) // max_frames))
    frame_indices = list(range(0, n, stride))
    if frame_indices[-1] != n - 1:
        frame_indices.append(n - 1)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.animation import FFMpegWriter
    except Exception as exc:
        raise RuntimeError(f"matplotlib/ffmpeg writer unavailable for fallback video: {exc}") from exc

    os.makedirs(os.path.dirname(output_mp4), exist_ok=True)

    def pad(series):
        if len(series) >= n:
            return series[:n]
        if not series:
            return [0.0] * n
        return series + [series[-1]] * (n - len(series))

    x = pad(x)
    y = pad(y)
    z = pad(z)
    vx = pad(vx)
    theta = pad(theta)
    if len(time_series) >= n:
        t = time_series[:n]
    else:
        t = [i * float(Dt) for i in range(n)]

    fig = plt.figure(figsize=(10, 7))
    ax_traj = fig.add_subplot(2, 1, 1)
    ax_sig = fig.add_subplot(2, 1, 2)

    fps = max(5, min(30, 1.0 / (float(Dt) * stride)))
    writer = FFMpegWriter(fps=fps, metadata={"title": "WingLoop fallback video"})

    xmin, xmax = min(x), max(x)
    ymin, ymax = min(y), max(y)
    zmin, zmax = min(z), max(z)
    if xmin == xmax: xmax = xmin + 1
    if ymin == ymax: ymax = ymin + 1

    with writer.saving(fig, output_mp4, dpi=100):
        for idx in frame_indices:
            ax_traj.clear()
            ax_sig.clear()

            ax_traj.plot(x[:idx + 1], y[:idx + 1], color="#0072BD", linewidth=1.8)
            ax_traj.scatter([x[idx]], [y[idx]], color="#D95319", s=35)
            ax_traj.set_xlim(xmin, xmax)
            ax_traj.set_ylim(ymin, ymax)
            ax_traj.grid(True, linestyle="--", alpha=0.4)
            ax_traj.set_xlabel("X [m]")
            ax_traj.set_ylabel("Y [m]")
            ax_traj.set_title(f"WingLoop fallback trajectory | t = {t[idx]:.2f} s | Z = {z[idx]:.3g} m")

            if vx:
                ax_sig.plot(t[:idx + 1], vx[:idx + 1], label=vx_name or "Vx", color="#77AC30")
            if theta:
                ax_sig.plot(t[:idx + 1], theta[:idx + 1], label=theta_name or "theta", color="#A2142F")
            ax_sig.set_xlim(0, t[-1] if t[-1] > 0 else 1)
            ax_sig.grid(True, linestyle="--", alpha=0.4)
            ax_sig.set_xlabel("Time [s]")
            ax_sig.legend(loc="best")

            fig.tight_layout()
            writer.grab_frame()

    plt.close(fig)
    return output_mp4


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
    video_plot_options = {
        "camera_movement": True,
        "wake_plotting": False,
    }

    if generate_video:
        video_format = input("Video format (gif/mp4/webp) [default: gif]: ").strip().lower()
        if video_format not in {"gif", "mp4", "webp"}:
            video_format = "gif"

        video_quality = input("Quality (low/medium/high) [default: medium]: ").strip().lower()
        if video_quality not in {"low", "medium", "high"}:
            video_quality = "medium"

        video_plot_options["camera_movement"] = ask_yes_no(
            "Enable ASWING camera movement in the video? (y/n): ",
            default=True,
        )
        video_plot_options["wake_plotting"] = ask_yes_no(
            "Enable ASWING wake plotting in the video? (y/n): ",
            default=False,
        )

        print(f"[Video] Output format: {video_format} | quality: {video_quality}")
        print(
            "[Video] ASWING plot options: "
            f"camera_movement={video_plot_options['camera_movement']} | "
            f"wake_plotting={video_plot_options['wake_plotting']}"
        )

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
        gif_target_duration = float(os.environ.get("WINGLOOP_GIF_TARGET_DURATION", "10"))
        gif_target_fps = float(os.environ.get("WINGLOOP_GIF_TARGET_FPS", "15"))
        default_max_video_frames = int(gif_target_duration * gif_target_fps) if video_format == "gif" else 600
        max_video_frames = int(os.environ.get("WINGLOOP_VIDEO_MAX_FRAMES", str(default_max_video_frames)))
        max_video_frames = max(50, max_video_frames)
        video_timeout = float(os.environ.get("WINGLOOP_VIDEO_PS_TIMEOUT", "60"))
        video_chunk_duration = float(os.environ.get("WINGLOOP_VIDEO_CHUNK_DURATION", "10"))
        video_chunk_duration = max(Dt, min(video_chunk_duration, 10.0))
        movie_speed_factor = float(
            os.environ.get(
                "WINGLOOP_VIDEO_SPEED_FACTOR",
                str(max(1.0, float(T_sim) / 5.0)),
            )
        )

        if video_format == "gif":
            if video_quality != "high":
                print("[Video] GIF export selected: using high quality preview settings.")
                video_quality = "high"
            print(
                f"[Video] GIF target: duration <= {gif_target_duration:.1f}s, "
                f"about {gif_target_fps:.1f} fps, max_frames={max_video_frames}."
            )
        elif T_sim > 60 and video_quality != "low":
            print("[Video] Long simulation detected: using low quality for faster export.")
            video_quality = "low"
        elif T_sim > 20 and video_quality == "high":
            print("[Video] Long simulation detected: using medium quality for faster export.")
            video_quality = "medium"

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
                movie_time_limit=T_sim,
                Dt=Dt,
                movie_chunk_duration=video_chunk_duration,
                movie_speed_factor=movie_speed_factor,
                plot_options=video_plot_options,
                stable_duration=4.0,
                poll_interval=1.0,
                timeout=video_timeout,
            )

            print(f"[Video] PostScript generated: {ps_path}")

            out_path = Generate_Analysis_Videos(
                ps_path,
                Dt=Dt,
                videofile=video_format,
                transpose=1,
                quality=video_quality,
                keep_frames=False,
                max_frames=max_video_frames,
                target_duration=gif_target_duration if video_format == "gif" else None,
            )

            print(f"[Video] Video saved: {out_path}")

        except Exception as exc:
            print(f"[Video] Error during video generation: {exc}")
            print("[Video] Make sure ghostscript and ffmpeg are installed:")
            print("        sudo apt install ghostscript ffmpeg")
            print("[Video] Falling back to a lightweight MP4 generated from sim_results.json...")

            try:
                fallback_mp4 = generate_fallback_video_from_json(
                    results_json=os.path.join(aswing_working_dir, result_name + ".json"),
                    output_mp4=os.path.join(aswing_working_dir, "videos", result_name + "_fallback.mp4"),
                    Dt=Dt,
                    max_frames=max_video_frames,
                )
                print(f"[Video] Fallback video saved: {fallback_mp4}")
            except Exception as fallback_exc:
                print(f"[Video] Fallback video failed: {fallback_exc}")

    print(f"\n[WingLoop] Total elapsed time: {time.time() - start_time_total:.2f} s")


if __name__ == "__main__":
    main()
