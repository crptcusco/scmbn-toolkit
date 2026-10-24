import argparse
import json
import logging
import os
import sys
import time
import traceback
import csv
import subprocess
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List, Tuple
import resource

# Dynamically locate the project root (cbn_core)

current_dir = Path(__file__).resolve().parent

root_dir = current_dir

while not (root_dir / "cbn_python").exists() and root_dir.parent != root_dir:

    root_dir = root_dir.parent



sys.path.append(str(root_dir / "cbn_python" / "src"))



from cbnetwork.cbnetwork import CBN



try:

    from cbnetwork.utils.logging_config import setup_logging

    setup_logging()

except ImportError:

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")



logger = logging.getLogger(__name__)



# Define the global path to the C++ binary (CPP_BINARY)

CPP_BINARY = root_dir / "cbn_cpp" / "build" / "scientific_benchmarking"



def validate_config(config: Dict[str, Any]) -> bool:

    """Basic validation of the configuration object."""

    required_keys = ["n_networks", "v_topology", "n_var_network"]

    for key in required_keys:

        if key not in config:

            logger.error(f"Missing required configuration key: {key}")

            return False

    return True



def load_identical_cbn(topology_path: Path) -> CBN:

    """Load a clean CBN from JSON to avoid cache contamination."""

    if hasattr(CBN, 'from_json'):

        return CBN.from_json(str(topology_path))

    elif hasattr(CBN, 'load_json'):

        return CBN.load_json(str(topology_path))

    else:

        return CBN(str(topology_path))

def execute_python_profile(cbn: CBN, profile: str) -> Tuple[float, float, float, float, float, float, float, float, int, int, int]:
    """Run the Python methods for a profile and return their metrics, including memory usage."""
    t_p1 = t_p2 = t_p3 = 0.0
    peak1 = peak2 = peak3 = 0.0

    logger.info(f"--- Starting tracemalloc memory profiling for: {profile} ---")
    
    if profile == "seq":
        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.find_attractors_duvrova()
        t_p1 = time.perf_counter() - t0
        current, peak1 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P1] find_attractors_duvrova -> Peak memory: {peak1 / 10**6:.2f} MB")

        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.find_compatible_pairs()
        t_p2 = time.perf_counter() - t0
        current, peak2 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P2] find_compatible_pairs -> Peak memory: {peak2 / 10**6:.2f} MB")

        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.mount_stable_attractor_fields()
        t_p3 = time.perf_counter() - t0
        current, peak3 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P3] mount_stable_attractor_fields -> Peak memory: {peak3 / 10**6:.2f} MB")

    elif profile == "par":
        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.find_local_attractors_parallel()
        t_p1 = time.perf_counter() - t0
        current, peak1 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P1] find_local_attractors_parallel -> Peak memory: {peak1 / 10**6:.2f} MB")

        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.find_compatible_pairs_parallel()
        t_p2 = time.perf_counter() - t0
        current, peak2 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P2] find_compatible_pairs_parallel -> Peak memory: {peak2 / 10**6:.2f} MB")

        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.mount_stable_attractor_fields_parallel()
        t_p3 = time.perf_counter() - t0
        current, peak3 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P3] mount_stable_attractor_fields_parallel -> Peak memory: {peak3 / 10**6:.2f} MB")

    elif profile == "weights":
        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.find_local_attractors_parallel_with_weights()
        t_p1 = time.perf_counter() - t0
        current, peak1 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P1] find_local_attractors_parallel_with_weights -> Peak memory: {peak1 / 10**6:.2f} MB")

        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.find_compatible_pairs_parallel_with_weights()
        t_p2 = time.perf_counter() - t0
        current, peak2 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P2] find_compatible_pairs_parallel_with_weights -> Peak memory: {peak2 / 10**6:.2f} MB")

        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.mount_stable_attractor_fields_parallel_chunks()
        t_p3 = time.perf_counter() - t0
        current, peak3 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P3] mount_stable_attractor_fields_parallel_chunks -> Peak memory: {peak3 / 10**6:.2f} MB")

    else:
        raise ValueError(f"Unknown python profile: {profile}")

    total_t = t_p1 + t_p2 + t_p3
    
    # Extract topology metrics from the solved network
    n_attr = cbn.get_n_local_attractors()
    n_pairs = cbn.get_n_pair_attractors()
    n_fields = cbn.get_n_attractor_fields()

    # Convertir bytes a KB
    mem_p1_kb = peak1 / 1024.0
    mem_p2_kb = peak2 / 1024.0
    mem_p3_kb = peak3 / 1024.0
    mem_total_kb = max(peak1, peak2, peak3) / 1024.0

    return t_p1, t_p2, t_p3, total_t, mem_p1_kb, mem_p2_kb, mem_p3_kb, mem_total_kb, n_attr, n_pairs, n_fields

# ... [The rest of the file remains unchanged from def execute_cpp_profiles onward] ...

def execute_cpp_profiles(topo_path: Path, exp_dir: Path) -> Dict[str, Tuple[float, float, float, float, float, float, float, float, int, int, int]]:
    """Run C++ once and extract metrics for its three strategies."""
    if not CPP_BINARY.exists():
        raise FileNotFoundError(f"C++ binary not found at: {CPP_BINARY}. Please build it first using 'make build-cpp'.")

    # C++ execution command
    cmd = [
        str(CPP_BINARY),
        "--samples", "1",
        "--input", str(topo_path),
        "--dir", str(exp_dir)
    ]

    logger.info(f"Invoking C++ with command: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    
    # --- Capture the C++ process's peak RAM usage on Linux ---
    rusage_children = resource.getrusage(resource.RUSAGE_CHILDREN)
    # On Linux, ru_maxrss is reported in kilobytes (KB); divide by 1024 to get MB.
    max_rss_mb = rusage_children.ru_maxrss / 1024.0
    logger.info(f"[C++ Engine] Peak memory (subprocess max RSS): {max_rss_mb:.2f} MB")
    # ----------------------------------------------------------------------

    if result.returncode != 0:
        raise RuntimeError(f"C++ engine crashed with return code {result.returncode}.\nStderr: {result.stderr}\nStdout: {result.stdout}")

    strategy_files = {
        "cpp_seq": "Traditional",
        "cpp_par": "SimpleParallel",
        "cpp_adv": "AdvancedParallel",
    }
    metrics = {}
    for profile, strategy in strategy_files.items():
        cpp_dyn_file = exp_dir / f"cbn_sample_1_{strategy}_dynamics.json"
        if not cpp_dyn_file.exists():
            raise FileNotFoundError(
                f"C++ dynamics output for {strategy} not found: {cpp_dyn_file}"
            )

        logger.info("C++ dynamics output file found for %s: %s", strategy, cpp_dyn_file)
        with open(cpp_dyn_file, "r") as f:
            json_data = json.load(f)

        perf_data = json_data.get("performance", {})
        t_p1 = perf_data.get("step_1_ms", 0.0) / 1000.0
        t_p2 = perf_data.get("step_2_ms", 0.0) / 1000.0
        t_p3 = perf_data.get("step_3_ms", 0.0) / 1000.0
        total_t = perf_data.get("total_ms", 0.0) / 1000.0

        # Extract C++ heap memory metrics
        mem_p1_kb = perf_data.get("mem_p1_kb", 0.0)
        mem_p2_kb = perf_data.get("mem_p2_kb", 0.0)
        mem_p3_kb = perf_data.get("mem_p3_kb", 0.0)
        mem_total_kb = perf_data.get("mem_total_kb", 0.0)

        step1 = json_data.get("pipeline_execution", {}).get("step_1_local_attractors", [])
        n_attractors = sum(len(item.get("attractors", [])) for item in step1)
        step2 = json_data.get("pipeline_execution", {}).get("step_2_compatible_pairs", [])
        n_pairs = len(step2)
        step3 = json_data.get("pipeline_execution", {}).get("step_3_global_fields", {})
        n_fields = len(step3.get("attractor_fields", []))
        metrics[profile] = (t_p1, t_p2, t_p3, total_t, mem_p1_kb, mem_p2_kb, mem_p3_kb, mem_total_kb, n_attractors, n_pairs, n_fields)

    return metrics

def run_pipeline(config: Dict[str, Any], sample_id: int, experiment_name: str, output_base: Path, csv_path: Path, fieldnames: List[str]):
    """Generate and save the base topology, process it with all 4 methods, and write results to CSV immediately."""
    exp_dir = output_base / "data" / experiment_name
    exp_dir.mkdir(parents=True, exist_ok=True)
    
    n_nets = config.get("n_networks", 0)

    # 1. Generate and save the master network
    logger.info(f"[{experiment_name}] Generating base topology...")
    cbn_base = CBN.generate_from_config(config)
    topo_path = exp_dir / "topology.json"
    cbn_base.to_json(str(topo_path))

    # 2. Run Python profiles on identical copies.
    profiles = ["seq", "par", "weights"]

    for profile in profiles:
        logger.info(f"[{experiment_name}] Running profile: {profile.upper()}...")
        
        try:
            # Load a clean, unsolved network
            cbn_instance = load_identical_cbn(topo_path)
            # Process and measure runtime and memory
            tp1, tp2, tp3, total, mp1, mp2, mp3, mtot, n_attr, n_pairs, n_fields = execute_python_profile(cbn_instance, profile)

            # Save Python-specific JSON for debugging
            with open(exp_dir / f"fields_{profile}.json", "w") as f:
                json.dump(cbn_instance.to_json_fields(), f, indent=4)

            row = {
                "sample": sample_id,
                "n_nets": n_nets,
                "perfil": profile,
                "t_p1": tp1,
                "t_p2": tp2,
                "t_p3": tp3,
                "total_t": total,
                "mem_p1_kb": mp1,
                "mem_p2_kb": mp2,
                "mem_p3_kb": mp3,
                "mem_total_kb": mtot,
                "n_attractors": n_attr,
                "n_pairs": n_pairs,
                "n_fields": n_fields
            }

        except Exception as e:
            logger.error(f"[{experiment_name}] Error en perfil {profile.upper()}: {e}")
            logger.debug(traceback.format_exc())
            # On error, persist a record with default/error values
            row = {
                "sample": sample_id,
                "n_nets": n_nets,
                "perfil": profile,
                "t_p1": 0.0,
                "t_p2": 0.0,
                "t_p3": 0.0,
                "total_t": 0.0,
                "mem_p1_kb": 0.0,
                "mem_p2_kb": 0.0,
                "mem_p3_kb": 0.0,
                "mem_total_kb": 0.0,
                "n_attractors": 0,
                "n_pairs": 0,
                "n_fields": 0
            }

        # Escribir inmediatamente al CSV (modo append)
        with open(csv_path, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            row_formatted = {k: (f"{v:.6f}" if isinstance(v, float) else v) for k, v in row.items()}
            writer.writerow(row_formatted)

        logger.info(f"[{experiment_name}] {profile.upper()} profile completed and saved to CSV.")

    # The C++ executable runs all three strategies in a single invocation.
    try:
        cpp_metrics = execute_cpp_profiles(topo_path, exp_dir)
        for profile, values in cpp_metrics.items():
            tp1, tp2, tp3, total, mp1, mp2, mp3, mtot, n_attr, n_pairs, n_fields = values
            row = {
                "sample": sample_id, "n_nets": n_nets, "perfil": profile,
                "t_p1": tp1, "t_p2": tp2, "t_p3": tp3, "total_t": total,
                "mem_p1_kb": mp1, "mem_p2_kb": mp2, "mem_p3_kb": mp3, "mem_total_kb": mtot,
                "n_attractors": n_attr, "n_pairs": n_pairs, "n_fields": n_fields,
            }
            with open(csv_path, 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow({k: (f"{v:.6f}" if isinstance(v, float) else v) for k, v in row.items()})
            logger.info(f"[{experiment_name}] {profile.upper()} profile completed and saved to CSV.")
    except Exception as e:
        logger.error(f"[{experiment_name}] Error in C++ profiles: {e}")

def main():
    parser = argparse.ArgumentParser(description="CBN All-in-One Hybrid Benchmark Processor")
    parser.add_argument("--config", type=str, required=True, help="Path to input JSON config")
    parser.add_argument("--output", type=str, default="results", help="Base directory for outputs")

    args = parser.parse_args()
    config_path = Path(args.config)
    output_base = Path(args.output)

    if not config_path.exists():
        logger.error(f"Configuration file {args.config} not found.")
        sys.exit(1)

    with open(config_path, "r") as f:
        data = json.load(f)

    configs = data if isinstance(data, list) else [data]

    # Ensure the output directory exists
    output_base.mkdir(parents=True, exist_ok=True)

    # --- CONFIGURAR CSV EN TIEMPO REAL ---
    csv_path = output_base / "benchmark_granular_workflow.csv"
    fieldnames = ["sample", "n_nets", "perfil", "t_p1", "t_p2", "t_p3", "total_t", "mem_p1_kb", "mem_p2_kb", "mem_p3_kb", "mem_total_kb", "n_attractors", "n_pairs", "n_fields"]
    
    # Create the file and write the header if it does not exist
    if not csv_path.exists():
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
        logger.info(f"Created new CSV file at: {csv_path}")
    else:
        logger.info(f"Using existing CSV file at: {csv_path} (append mode)")

    logger.info(f"Starting hybrid evaluation (4-in-1) for {len(configs)} configurations...")

    for i, cfg in enumerate(configs):
        if not validate_config(cfg):
            logger.warning(f"Skipping invalid configuration at index {i}")
            continue

        sample_id = i + 1
        exp_name = cfg.get("experiment_name", f"exp_{config_path.stem}_{sample_id}")
        
        logger.info(f"\n=========================================")
        logger.info(f"Processing sample {sample_id}/{len(configs)}: {exp_name}")
        logger.info(f"=========================================")
        
        # Run the full pipeline for the sample and write all 4 profiles to CSV immediately.
        run_pipeline(cfg, sample_id, exp_name, output_base, csv_path, fieldnames)

        logger.info(f"==> Sample {sample_id}/{len(configs)} completed.")

    logger.info(f"\nHybrid benchmark completed successfully. Final data: {csv_path}")

if __name__ == "__main__":
    main()
