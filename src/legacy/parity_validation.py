import json
import random
import subprocess
import sys
from pathlib import Path

# Configuración
N_SAMPLES = 100
TOPOLOGIES = [1, 2, 3, 7, 9]  # complete, linear, cycle, dm, sf
NETWORKS_RANGE = (3, 6)
VARS_RANGE = (3, 5)

ROOT_DIR = Path(__file__).resolve().parents[2]
CPP_BINARY = ROOT_DIR / "cbn_cpp" / "build" / "scientific_benchmarking"
PYTHON_GEN = ROOT_DIR / "experiments" / "mix" / "cbn_python_gen.py"
PYTHON_SOLVER = ROOT_DIR / "experiments" / "mix" / "cbn_python_solver.py"
TEMP_DIR = ROOT_DIR / "temp_parity"
TEMP_DIR.mkdir(exist_ok=True)


def run_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return False, result.stderr
    return True, result.stdout


def compare_attractors(py_dyn_file, cpp_dyn_file):
    with open(py_dyn_file) as f:
        py_data = json.load(f)
    with open(cpp_dyn_file) as f:
        cpp_data = json.load(f)

    def get_canonical(data):
        attrs = data.get("attractors", [])
        canonical = []
        for a in attrs:
            states = a.get("states", [])
            # Some formats might have id as string or int
            canonical.append(tuple(sorted([int(s) for s in states])))
        return sorted(canonical)

    py_can = get_canonical(py_data)
    cpp_can = get_canonical(cpp_data)

    return py_can == cpp_can, py_can, cpp_can


def main():
    print(f"Starting Parity Validation: {N_SAMPLES} random samples")

    if not CPP_BINARY.exists():
        print(f"Error: C++ Binary not found at {CPP_BINARY}. Run build first.")
        return

    success_count = 0
    for i in range(1, N_SAMPLES + 1):
        topo = random.choice(TOPOLOGIES)
        nets = random.randint(*NETWORKS_RANGE)
        vars = random.randint(*VARS_RANGE)

        topo_file = TEMP_DIR / f"topo_{i}.json"
        py_dyn = TEMP_DIR / f"py_dyn_{i}.json"
        cpp_dyn = TEMP_DIR / f"cpp_dyn_{i}.json"

        # 1. Generate topology
        success, err = run_command(
            [
                sys.executable,
                str(PYTHON_GEN),
                "--topology",
                str(topo),
                "--networks",
                str(nets),
                "--vars",
                str(vars),
                "--output",
                str(topo_file),
            ]
        )
        if not success:
            print(f"Sample {i}: Python Gen failed: {err}")
            continue

        # 2. Python Solve
        success, err = run_command(
            [
                sys.executable,
                str(PYTHON_SOLVER),
                "--input",
                str(topo_file),
                "--output",
                str(py_dyn),
            ]
        )
        if not success:
            print(f"Sample {i}: Python Solver failed: {err}")
            continue

        # 3. C++ Solve
        success, err = run_command(
            [
                str(CPP_BINARY),
                "--input",
                str(topo_file),
                "--dir",
                str(TEMP_DIR),
                "--samples",
                "1",
            ]
        )
        if not success:
            print(f"Sample {i}: C++ Solver failed: {err}")
            continue

        cpp_gen = TEMP_DIR / "cbn_sample_1_AdvancedParallel_dynamics.json"
        if cpp_gen.exists():
            cpp_gen.replace(cpp_dyn)
        else:
            print(f"Sample {i}: C++ didn't produce expected file")
            continue

        # 4. Compare
        match, py_res, cpp_res = compare_attractors(py_dyn, cpp_dyn)
        if match:
            success_count += 1
            print(
                f"[{i}/{N_SAMPLES}] OK | Topo:{topo} Nets:{nets} Vars:{vars} | Fields: {len(py_res)}"
            )
        else:
            print(
                f"[{i}/{N_SAMPLES}] FAILED PARITY! | Topo:{topo} Nets:{nets} Vars:{vars}"
            )
            print(f"  Python: {py_res}")
            print(f"  C++   : {cpp_res}")

            # State dump for debugging
            print("\n--- Generating Debug State Dumps ---")
            run_command(
                [
                    sys.executable,
                    str(PYTHON_SOLVER),
                    "--input",
                    str(topo_file),
                    "--output",
                    str(TEMP_DIR / "debug_py_dyn.json"),
                    "--debug-dump",
                ]
            )
            run_command(
                [
                    str(CPP_BINARY),
                    "--input",
                    str(topo_file),
                    "--dir",
                    str(TEMP_DIR),
                    "--samples",
                    "1",
                    "--debug-dump",
                ]
            )
            sys.exit(1)

    print(f"\nSUCCESS: {success_count}/{N_SAMPLES} samples matched perfectly.")


if __name__ == "__main__":
    main()
