import argparse
import csv
import json
import random
import subprocess
import sys
import logging
from pathlib import Path

# ======================================================================
# CONFIGURACIÓN DEL EXPERIMENTO
# ======================================================================
N_SAMPLES = 5  

MIX_DIR = Path(__file__).resolve().parent
ROOT_DIR = MIX_DIR.parents[1]
CPP_BINARY = ROOT_DIR / "cbn_cpp" / "build" / "scientific_benchmarking"
PYTHON_GEN = MIX_DIR / "cbn_python_gen.py"
PYTHON_SOLVER = MIX_DIR / "cbn_python_solver.py"
OUTPUT_DIR = MIX_DIR / "output"
OUTPUT_CSV = OUTPUT_DIR / "final_comparative_benchmark.csv"

OUTPUT_DIR.mkdir(exist_ok=True)

def run_command(cmd):
    try:
        # Añadimos check=False para gestionar el error manualmente
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            # Capturamos el error específico del binario
            error_msg = f"Code {result.returncode}: {result.stderr.strip()}"
            return False, error_msg
            
        return True, result.stdout.strip()
        
    except FileNotFoundError:
        return False, "Binario de C++ no encontrado en la ruta especificada."
    except Exception as e:
        return False, f"Error inesperado en la ejecución: {str(e)}"

def compare_dynamics(py_root, cpp_root):
    def get_canonical_fields(root_data, label):
        exec_data = root_data.get("pipeline_execution", {})
        step3 = exec_data.get("step_3_global_fields", {})
        fields = step3.get("attractor_fields", [])
        
        canonical = []
        for f in fields:
            if "attractor_indices" in f:
                canonical.append(tuple(sorted(f["attractor_indices"])))
            elif "assembled_from_attractors" in f:
                indices = [item["attr"] for item in f["assembled_from_attractors"]]
                canonical.append(tuple(sorted(indices)))
        
        res = sorted(canonical)
        print(f"DEBUG: {label} fields -> {res}") # <-- ESTA LÍNEA ES CLAVE
        return res

    py_fields = get_canonical_fields(py_root, "PYTHON")
    cpp_fields = get_canonical_fields(cpp_root, "C++")

    return (py_fields == cpp_fields), (py_fields, cpp_fields)

def main():
    parser = argparse.ArgumentParser(description="CBN Hybrid Benchmark Orchestrator")
    parser.add_argument("--topology", type=int, default=2, help="ID de la topologia (ej. 4 para Lineal)")
    parser.add_argument("--networks", type=int, default=6, help="Numero de redes locales")
    parser.add_argument("--vars", type=int, default=5, help="Variables por red")
    args = parser.parse_args()

    print("=== CBN HYBRID BENCHMARK ORCHESTRATOR ===")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Config: {args.networks} networks x {args.vars} variables | Topology ID: {args.topology}")
    print("=========================================")

    if not CPP_BINARY.exists():
        print(f"[Error] C++ Binary not found at {CPP_BINARY}.")
        return

    with open(OUTPUT_CSV, mode="w", newline="") as csv_file:
        fieldnames = ["sample_id", "topology", "py_time_ms", "cpp_time_ms", "speedup", "status", "fields"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(1, N_SAMPLES + 1):
            print(f"\n[*] Sample {i}/{N_SAMPLES} | Topology: {args.topology}")

            topo_file = OUTPUT_DIR / f"cbn_sample_{i}_topology.json"
            py_dyn_file = OUTPUT_DIR / f"py_sample_{i}_dynamics.json"
            cpp_dyn_file = OUTPUT_DIR / f"cpp_sample_{i}_dynamics.json"

            # 1. Generate
            success, out = run_command([
                sys.executable, str(PYTHON_GEN),
                "--topology", str(args.topology),
                "--networks", str(args.networks),
                "--vars", str(args.vars),
                "--output", str(topo_file)
            ])
            if not success:
                print(f"[Error] Python Generator failed: {out}")
                break

            # 2. Python Solve
            success, out = run_command([
                sys.executable, str(PYTHON_SOLVER),
                "--input", str(topo_file),
                "--output", str(py_dyn_file)
            ])
            if not success:
                print(f"[Error] Python Solver failed: {out}")
                break

            with open(py_dyn_file) as f:
                py_res = json.load(f)
                py_time = py_res["performance"]["total_ms"]

            # 3. C++ Solve
            cmd = [
                str(CPP_BINARY),
                "--samples", "1",
                "--input", str(topo_file),
                "--dir", str(OUTPUT_DIR)
            ]
            print(f"[DEBUG] Ejecutando C++ con input: {cmd[cmd.index('--input') + 1]}")
            success, out = run_command([
                str(CPP_BINARY),
                "--samples", "1",
                "--input", str(topo_file),
                "--dir", str(OUTPUT_DIR)
            ])
            
            if not success:
                print(f"[Error] C++ execution crashed:\n{out}")
                writer.writerow({"sample_id": i, "topology": args.topology, "status": "CPP_CRASH"})
                continue

            # Buscar CUALQUIER archivo que C++ haya generado que contenga 'dynamics'
            # para evitar el fallo por nombre rígido
            cpp_generated_files = list(OUTPUT_DIR.glob("*dynamics*.json"))
            cpp_gen_file = None
            
            for file_path in cpp_generated_files:
                if file_path != py_dyn_file and file_path != cpp_dyn_file:
                    cpp_gen_file = file_path
                    break

            if cpp_gen_file and cpp_gen_file.exists():
                cpp_gen_file.replace(cpp_dyn_file)
            else:
                print(f"[Error] El C++ terminó pero no se encontró un archivo JSON de salida reconocible.")
                print(f"Salida de consola del C++:\n{out}")
                break

            with open(cpp_dyn_file) as f:
                cpp_res = json.load(f)
                # Performance moved to "performance" (wait, I used "performance" in C++ or "metrics"?)
                # Looking at my cat for scientific_benchmarking.cpp: j_out["performance"] = { ... }
                cpp_time = cpp_res["performance"]["total_ms"]

            # 4. Compare
            is_equal, result = compare_dynamics(py_res, cpp_res)

            if is_equal:
                speedup = py_time / cpp_time if cpp_time > 0 else 0
                print(f"[OK] Parity match! Fields: {result}")
                writer.writerow({
                    "sample_id": i, "topology": args.topology,
                    "py_time_ms": py_time, "cpp_time_ms": cpp_time,
                    "speedup": speedup, "status": "SUCCESS", "fields": result
                })
            else:
                print(f"🚨 [ERROR] PARITY DIVERGENCE in sample {i}!")
                writer.writerow({"sample_id": i, "topology": args.topology, "status": "PARITY_ERROR"})
                break

            csv_file.flush()

    print(f"\n[DONE] Benchmark report saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
