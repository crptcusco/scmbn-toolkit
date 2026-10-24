import argparse
import json
import logging
import sys
import traceback
import csv
import subprocess
import resource
from pathlib import Path
from typing import Any, Dict, List, Tuple

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

def execute_cpp_profiles(topo_path: Path, exp_dir: Path, v_topology: int = 2, n_networks: int = 4, n_vars: int = 5) -> Dict[str, Tuple[float, float, float, float, float, float, float, float, int, int, int]]:
    """Run C++ once and extract metrics for its three strategies."""
    if not CPP_BINARY.exists():
        raise FileNotFoundError(f"C++ binary not found at: {CPP_BINARY}. Please build it first using 'make build-cpp'.")

    # C++ execution command
    cmd = [
        str(CPP_BINARY),
        "--samples", "1",
        "--topology", str(v_topology),
        "--networks", str(n_networks),
        "--vars", str(n_vars),
        "--input", str(topo_path),
        "--dir", str(exp_dir)
    ]

    logger.info(f"Invoking C++ with command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    
    # Capture the C++ process's peak RAM usage on Linux
    rusage_children = resource.getrusage(resource.RUSAGE_CHILDREN)
    max_rss_mb = rusage_children.ru_maxrss / 1024.0
    logger.info(f"[C++ Engine] Peak memory (subprocess max RSS): {max_rss_mb:.2f} MB")

    if result.returncode != 0:
        raise RuntimeError(f"C++ engine crashed with return code {result.returncode}.\nStderr: {result.stderr}\nStdout: {result.stdout}")

    # strategy_files = {
    #     "cpp_seq": "Traditional",
    #     "cpp_par": "SimpleParallel",
    #     "cpp_adv": "AdvancedParallel",
    # }

    strategy_files = {
    "cpp_adv": "AdvancedParallel",
    }

    metrics = {}
    for profile, strategy in strategy_files.items():
        cpp_dyn_file = exp_dir / f"cbn_sample_1_{strategy}_dynamics.json"
        if not cpp_dyn_file.exists():
            raise FileNotFoundError(
                f"C++ dynamics output for {strategy} not found: {cpp_dyn_file}"
            )

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
    """Generate the base topology and process it using only C++."""
    exp_dir = output_base / "data" / experiment_name
    exp_dir.mkdir(parents=True, exist_ok=True)
    
    n_nets = config.get("n_networks", 0)
    v_topology = config.get("v_topology", 2)
    n_var_network = config.get("n_var_network", 5)

    # 1. Generate and save the master network
    logger.info(f"[{experiment_name}] Generating base topology...")
    cbn_base = CBN.generate_from_config(config)
    topo_path = exp_dir / "topology.json"
    cbn_base.to_json(str(topo_path))

    # 2. Run only the C++ engine
    try:
        cpp_metrics = execute_cpp_profiles(topo_path, exp_dir, v_topology=v_topology, n_networks=n_nets, n_vars=n_var_network)
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
        logger.debug(traceback.format_exc())

def main():
    parser = argparse.ArgumentParser(description="CBN C++ Exclusive Benchmark Processor")
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
    output_base.mkdir(parents=True, exist_ok=True)

    csv_path = output_base / "benchmark_cbn_cpp_exclusive.csv"
    fieldnames = ["sample", "n_nets", "perfil", "t_p1", "t_p2", "t_p3", "total_t", "mem_p1_kb", "mem_p2_kb", "mem_p3_kb", "mem_total_kb", "n_attractors", "n_pairs", "n_fields"]
    
    if not csv_path.exists():
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
        logger.info(f"Created new CSV file at: {csv_path}")
    else:
        logger.info(f"Using existing CSV file at: {csv_path} (append mode)")

    logger.info(f"Starting C++-only evaluation for {len(configs)} configurations...")

    for i, cfg in enumerate(configs):
        if not validate_config(cfg):
            continue

        sample_id = i + 1
        exp_name = cfg.get("experiment_name", f"exp_{config_path.stem}_{sample_id}")
        
        logger.info(f"\n=========================================")
        logger.info(f"Processing sample {sample_id}/{len(configs)}: {exp_name}")
        logger.info(f"=========================================")
        
        run_pipeline(cfg, sample_id, exp_name, output_base, csv_path, fieldnames)
        logger.info(f"==> Sample {sample_id}/{len(configs)} completed.")

if __name__ == "__main__":
    main()