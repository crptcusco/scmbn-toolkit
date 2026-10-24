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

# Búsqueda dinámica de la raíz del proyecto (cbn_core)

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



# Definir la ruta global al binario de C++ (CPP_BINARY)

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

    """Helper para cargar una CBN limpia desde el JSON y evitar contaminación de caché."""

    if hasattr(CBN, 'from_json'):

        return CBN.from_json(str(topology_path))

    elif hasattr(CBN, 'load_json'):

        return CBN.load_json(str(topology_path))

    else:

        return CBN(str(topology_path))

def execute_python_profile(cbn: CBN, profile: str) -> Tuple[float, float, float, float, float, float, float, float, int, int, int]:
    """Ejecuta los métodos exactos de Python correspondientes al perfil y retorna sus métricas, incluyendo log de memoria."""
    t_p1 = t_p2 = t_p3 = 0.0
    peak1 = peak2 = peak3 = 0.0

    logger.info(f"--- Iniciando perfilado de memoria tracemalloc para: {profile} ---")
    
    if profile == "seq":
        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.find_attractors_duvrova()
        t_p1 = time.perf_counter() - t0
        current, peak1 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P1] find_attractors_duvrova -> Memoria Pico: {peak1 / 10**6:.2f} MB")

        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.find_compatible_pairs()
        t_p2 = time.perf_counter() - t0
        current, peak2 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P2] find_compatible_pairs -> Memoria Pico: {peak2 / 10**6:.2f} MB")

        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.mount_stable_attractor_fields()
        t_p3 = time.perf_counter() - t0
        current, peak3 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P3] mount_stable_attractor_fields -> Memoria Pico: {peak3 / 10**6:.2f} MB")

    elif profile == "par":
        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.find_local_attractors_parallel()
        t_p1 = time.perf_counter() - t0
        current, peak1 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P1] find_local_attractors_parallel -> Memoria Pico: {peak1 / 10**6:.2f} MB")

        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.find_compatible_pairs_parallel()
        t_p2 = time.perf_counter() - t0
        current, peak2 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P2] find_compatible_pairs_parallel -> Memoria Pico: {peak2 / 10**6:.2f} MB")

        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.mount_stable_attractor_fields_parallel()
        t_p3 = time.perf_counter() - t0
        current, peak3 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P3] mount_stable_attractor_fields_parallel -> Memoria Pico: {peak3 / 10**6:.2f} MB")

    elif profile == "weights":
        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.find_local_attractors_parallel_with_weights()
        t_p1 = time.perf_counter() - t0
        current, peak1 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P1] find_local_attractors_parallel_with_weights -> Memoria Pico: {peak1 / 10**6:.2f} MB")

        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.find_compatible_pairs_parallel_with_weights()
        t_p2 = time.perf_counter() - t0
        current, peak2 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P2] find_compatible_pairs_parallel_with_weights -> Memoria Pico: {peak2 / 10**6:.2f} MB")

        tracemalloc.start()
        t0 = time.perf_counter()
        cbn.mount_stable_attractor_fields_parallel_chunks()
        t_p3 = time.perf_counter() - t0
        current, peak3 = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(f"[{profile} - P3] mount_stable_attractor_fields_parallel_chunks -> Memoria Pico: {peak3 / 10**6:.2f} MB")

    else:
        raise ValueError(f"Unknown python profile: {profile}")

    total_t = t_p1 + t_p2 + t_p3
    
    # Extraer métricas topológicas de la red resuelta
    n_attr = cbn.get_n_local_attractors()
    n_pairs = cbn.get_n_pair_attractors()
    n_fields = cbn.get_n_attractor_fields()

    # Convertir bytes a KB
    mem_p1_kb = peak1 / 1024.0
    mem_p2_kb = peak2 / 1024.0
    mem_p3_kb = peak3 / 1024.0
    mem_total_kb = max(peak1, peak2, peak3) / 1024.0

    return t_p1, t_p2, t_p3, total_t, mem_p1_kb, mem_p2_kb, mem_p3_kb, mem_total_kb, n_attr, n_pairs, n_fields

# ... [El resto del archivo se mantiene exactamente igual a partir de def execute_cpp_profiles] ...

def execute_cpp_profiles(topo_path: Path, exp_dir: Path) -> Dict[str, Tuple[float, float, float, float, float, float, float, float, int, int, int]]:
    """Ejecuta C++ una vez y extrae las métricas de sus tres estrategias."""
    if not CPP_BINARY.exists():
        raise FileNotFoundError(f"C++ binary not found at: {CPP_BINARY}. Please build it first using 'make build-cpp'.")

    # Comando de ejecución C++
    cmd = [
        str(CPP_BINARY),
        "--samples", "1",
        "--input", str(topo_path),
        "--dir", str(exp_dir)
    ]

    logger.info(f"Invocando C++ con comando: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    
    # --- NUEVO: Capturar el pico máximo de RAM del proceso C++ en Linux ---
    rusage_children = resource.getrusage(resource.RUSAGE_CHILDREN)
    # En Linux, ru_maxrss se reporta en Kilobytes (KB), dividimos por 1024 para MB
    max_rss_mb = rusage_children.ru_maxrss / 1024.0
    logger.info(f"[C++ Engine] Memoria Pico (Max RSS del subproceso): {max_rss_mb:.2f} MB")
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

        # Extraer métricas de memoria quirúrgica del heap de C++
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
    """Genera la topología base, la guarda, y la procesa con los 4 métodos, escribiendo inmediatamente al CSV."""
    exp_dir = output_base / "data" / experiment_name
    exp_dir.mkdir(parents=True, exist_ok=True)
    
    n_nets = config.get("n_networks", 0)

    # 1. Generar la "Red Maestra" y guardarla
    logger.info(f"[{experiment_name}] Generando topología base...")
    cbn_base = CBN.generate_from_config(config)
    topo_path = exp_dir / "topology.json"
    cbn_base.to_json(str(topo_path))

    # 2. Ejecutar los perfiles Python sobre copias idénticas.
    profiles = ["seq", "par", "weights"]

    for profile in profiles:
        logger.info(f"[{experiment_name}] Ejecutando perfil: {profile.upper()}...")
        
        try:
            # Cargar red limpia sin resolver
            cbn_instance = load_identical_cbn(topo_path)
            # Procesar y medir tiempos y memoria
            tp1, tp2, tp3, total, mp1, mp2, mp3, mtot, n_attr, n_pairs, n_fields = execute_python_profile(cbn_instance, profile)

            # Guardar JSON específico de Python para depuración
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
            # En caso de error, persistir registro con valores por defecto/error
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

        logger.info(f"[{experiment_name}] Perfil {profile.upper()} completado y persistido en CSV.")

    # El ejecutable C++ corre sus tres estrategias en una sola invocación.
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
            logger.info(f"[{experiment_name}] Perfil {profile.upper()} completado y persistido en CSV.")
    except Exception as e:
        logger.error(f"[{experiment_name}] Error en perfiles C++: {e}")

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

    # Asegurar que el directorio de salida existe
    output_base.mkdir(parents=True, exist_ok=True)

    # --- CONFIGURAR CSV EN TIEMPO REAL ---
    csv_path = output_base / "benchmark_granular_workflow.csv"
    fieldnames = ["sample", "n_nets", "perfil", "t_p1", "t_p2", "t_p3", "total_t", "mem_p1_kb", "mem_p2_kb", "mem_p3_kb", "mem_total_kb", "n_attractors", "n_pairs", "n_fields"]
    
    # Crear el archivo e inicializar cabeceras si no existe
    if not csv_path.exists():
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
        logger.info(f"Creado archivo CSV nuevo en: {csv_path}")
    else:
        logger.info(f"Usando archivo CSV existente en: {csv_path} (modo append)")

    logger.info(f"Iniciando evaluación híbrida (4-en-1) para {len(configs)} configuraciones...")

    for i, cfg in enumerate(configs):
        if not validate_config(cfg):
            logger.warning(f"Saltando configuración inválida en índice {i}")
            continue

        sample_id = i + 1
        exp_name = cfg.get("experiment_name", f"exp_{config_path.stem}_{sample_id}")
        
        logger.info(f"\n=========================================")
        logger.info(f"Procesando muestra {sample_id}/{len(configs)}: {exp_name}")
        logger.info(f"=========================================")
        
        # Ejecuta el pipeline completo para la muestra, que corre y escribe los 4 perfiles inmediatamente al CSV
        run_pipeline(cfg, sample_id, exp_name, output_base, csv_path, fieldnames)

        logger.info(f"==> Muestra {sample_id}/{len(configs)} finalizada.")

    logger.info(f"\n¡Benchmark híbrido completado con éxito! Datos finales en: {csv_path}")

if __name__ == "__main__":
    main()
