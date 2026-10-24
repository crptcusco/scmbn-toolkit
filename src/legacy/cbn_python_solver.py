import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).resolve().parents[2] / "cbn_python" / "src"))

from cbnetwork.cbnetwork import CBN  # noqa: E402


def run_audit(input_path: str):
    """
    Performs a comprehensive health check of the solver methods.
    """
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.", flush=True)
        return

    results = []
    detailed_logs = []  # Búfer en memoria para evitar que Numba/Hilos pisen los prints

    # 1. Attractor Finding Methods (Ya sin fuerza bruta)
    attractor_methods = [
        "find_attractors_duvrova",
        "find_attractors_brute_force",
        "find_local_attractors_parallel",
        "find_local_attractors_parallel_with_weights",
    ]

    # 2. Compatible Pairs Methods
    pairs_methods = [
        "find_compatible_pairs",
        "find_compatible_pairs_parallel",
        "find_compatible_pairs_parallel_with_weights",
    ]

    # 3. Attractor Field Methods
    field_methods = [
        "mount_stable_attractor_fields",
        "mount_stable_attractor_fields_parallel",
        "mount_stable_attractor_fields_parallel_chunks",
    ]

    def run_method(cbn, method_name, *args, **kwargs):
        method = getattr(cbn, method_name, None)
        if not method:
            return "MISSING", "Method not found", 0, 0

        start_time = time.perf_counter()
        try:
            method(*args, **kwargs)
            duration = time.perf_counter() - start_time

            count = 0
            if "attractor" in method_name and "field" not in method_name:
                count = cbn.get_n_local_attractors()
            elif "pair" in method_name:
                count = cbn.get_n_pair_attractors()
            elif "field" in method_name:
                count = cbn.get_n_attractor_fields()

            if count == 0 and "find" in method_name:
                return (
                    "OK",
                    f"Tiempo: {duration:.2f}s | Conteo: {count} (⚠️ WARNING: Empty results)",
                    duration,
                    count,
                )

            return (
                "OK",
                f"Tiempo: {duration:.2f}s | Conteo: {count}",
                duration,
                count,
            )
        except Exception as e:
            duration = time.perf_counter() - start_time
            err_msg = str(e)
            stack = traceback.extract_tb(sys.exc_info()[2])
            last_call = stack[-1] if stack else None
            loc = (
                f"({last_call.filename.split('/')[-1]}, Line {last_call.lineno})"
                if last_call
                else ""
            )
            return (
                "FAIL",
                f"ERROR: {type(e).__name__}: {err_msg} {loc}",
                duration,
                0,
            )

    # --- EJECUCIÓN SILENCIOSA (Acumulando datos) ---

    # Audit Attractor Methods
    for m in attractor_methods:
        cbn = CBN.from_json(input_path)
        status, msg, duration, count = run_method(
            cbn, m, use_brute_force=True if "sequential" in m else False
        )
        results.append((m, status, msg, count))
        detailed_logs.append((f"[{status:4}] {m:45} -> {msg}", "ATTRACTORS"))

    # For Pairs and Fields, use a base CBN that worked
    base_cbn = CBN.from_json(input_path)
    base_cbn.find_attractors_brute_force()

    for m in pairs_methods:
        for edge in base_cbn.l_directed_edges:
            edge.d_comp_pairs_attractors_by_value = {0: [], 1: []}

        status, msg, duration, count = run_method(base_cbn, m)
        results.append((m, status, msg, count))
        detailed_logs.append((f"[{status:4}] {m:45} -> {msg}", "PAIRS"))

    # Ensure we have pairs for field calculation
    base_cbn.find_compatible_pairs()

    for m in field_methods:
        base_cbn.d_attractor_fields = {}
        status, msg, duration, count = run_method(base_cbn, m)
        results.append((m, status, msg, count))
        detailed_logs.append((f"[{status:4}] {m:45} -> {msg}", "FIELDS"))

    # --- IMPRESIÓN DEL REPORTE UNIFICADO (Al final de todo) ---

    print("\n" + "=" * 70, flush=True)
    print("📊 REPORTE DE AUDITORÍA DE MÉTODOS DEL SOLVER - CBN_CORE", flush=True)
    print("=" * 70, flush=True)

    current_section = "ATTRACTORS"
    for log_line, section in detailed_logs:
        if section != current_section:
            print("-" * 70, flush=True)
            current_section = section
        print(log_line, flush=True)

    print("=" * 70, flush=True)
    print("🔍 VERIFICACIÓN DE PARIDAD CIENTÍFICA", flush=True)
    print("=" * 70, flush=True)

    def check_parity(group_name, methods_in_group):
        group_results = [
            r for r in results if r[0] in methods_in_group and r[1] == "OK" and r[3] > 0
        ]
        if not group_results:
            print(
                f"[WARN] No successful methods in group {group_name} to compare.",
                flush=True,
            )
            return

        counts = [r[3] for r in group_results]
        if len(set(counts)) > 1:
            print(f"🚨 ALERT: Divergence in {group_name}!", flush=True)
            for name, status, msg, count in group_results:
                print(f"   - {name}: {count}", flush=True)
        else:
            print(
                f"[OK] Parity maintained for {group_name} ({counts[0]} consistent results)",
                flush=True,
            )

    check_parity("Attractors", attractor_methods)
    check_parity("Compatible Pairs", pairs_methods)
    check_parity("Attractor Fields", field_methods)
    print(
        "======================================================================\n",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description="CBN Python Solver")
    parser.add_argument("--input", type=str, required=True, help="Input JSON file")
    parser.add_argument(
        "--output", type=str, required=False, help="Output dynamics JSON file"
    )
    parser.add_argument("--audit", action="store_true", help="Run diagnostic audit")

    args = parser.parse_args()

    # Set default output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    if not args.output:
        input_stem = Path(args.input).stem
        output_path = output_dir / f"{input_stem}_dynamics.json"
    else:
        # If output is absolute or relative path, ensure directory exists
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(args.input):
        print(f"[Error] Input file {args.input} not found.")
        sys.exit(1)

    # ... (después de cargar cbn)
    cbn = CBN.from_json(args.input)

    # INICIALIZAR VARIABLES PARA EVITAR EL NAMEERROR
    s2_ms = 0
    s3_ms = 0
    start_time = time.perf_counter()

    # Búsqueda de atractores
    cbn.find_attractors_duvrova()

    # Búsqueda de pares
    s2_start = time.perf_counter()
    cbn.find_compatible_pairs()

    if cbn.get_n_pair_attractors() == 0:
        cbn = CBN.from_json(args.input)
        cbn.find_attractors_duvrova()
        cbn.find_compatible_pairs()

    s2_ms = (time.perf_counter() - s2_start) * 1000

    # Paso de campos
    if len(cbn.l_directed_edges) > 0:
        s3_start = time.perf_counter()
        cbn.mount_stable_attractor_fields()
        s3_ms = (time.perf_counter() - s3_start) * 1000

    # CÁLCULO FINAL DE TIEMPO
    total_ms = (time.perf_counter() - start_time) * 1000

    # ... (ahora sí puedes usar total_ms en output_object)

    # Metadata
    topo_type = "N/A"
    if cbn.o_global_topology:
        topo_type = GlobalTopology.allowed_topologies.get(
            cbn.o_global_topology.v_topology, "Unknown"
        )

    output_object = {
        "topology_metadata": {
            "topology_type": topo_type,
            "topology_id": Path(args.input).stem,
            "nodes": len(cbn.l_local_networks),
            "v_elements": len(cbn.l_local_networks) * cbn.get_n_local_variables(),
        },
        "performance": {"total_ms": total_ms, "step_2_ms": s2_ms, "step_3_ms": s3_ms},
        "pipeline_execution": {
            "step_1_local_attractors": [],
            "step_2_compatible_pairs": [],
            "step_3_global_fields": {"attractor_fields": []},
        },
    }

    # Populate Step 1: Local Attractors (Unpacked)
    for net in cbn.l_local_networks:
        for scene in net.local_scenes:
            # l_values can be a list or None. If list, its first element is the scene string.
            scenario_str = ""
            if scene.l_values and len(scene.l_values) > 0:
                scenario_str = scene.l_values[0]

            net_scene = {
                "network_id": net.index,
                "applied_function": "Logic_CNF",
                "local_scenario": [int(c) for c in scenario_str],
                "attractors": [],
            }
            for attr in scene.l_attractors:
                attr_data = {
                    "attractor_id": attr.l_index,
                    "global_id": attr.g_index,
                    "length": len(attr.l_states),
                    "states_unpacked": [],
                }
                for state in attr.l_states:
                    vals = state.l_variable_values
                    if isinstance(vals, str):
                        vals = [int(c) for c in vals]

                    unpacked = {}
                    for i, v_idx in enumerate(net.internal_variables):
                        unpacked[f"var_{v_idx}"] = int(vals[i])
                    attr_data["states_unpacked"].append(unpacked)
                net_scene["attractors"].append(attr_data)
            output_object["pipeline_execution"]["step_1_local_attractors"].append(
                net_scene
            )

    # Populate Step 2: Compatible Pairs
    for edge in cbn.l_directed_edges:
        for val in [0, 1]:
            pairs = edge.d_comp_pairs_attractors_by_value.get(val, [])
            for p in pairs:
                output_object["pipeline_execution"]["step_2_compatible_pairs"].append(
                    {
                        "source_network": edge.output_local_network,
                        "target_network": edge.input_local_network,
                        "source_attractor_id": p[0],
                        "target_attractor_id": p[1],
                        "coupling_value": val,
                        "is_compatible": True,
                    }
                )

    # Populate Step 3: Global Fields
    for field_id, attractor_indices in cbn.d_attractor_fields.items():
        field_data = {
            "field_id": int(field_id),
            "attractor_indices": [int(idx) for idx in attractor_indices],
            "global_state_unpacked": [],
        }

        global_state = {}
        for g_idx in attractor_indices:
            attr = cbn.get_local_attractor_by_index(g_idx)
            if attr and attr.l_states:
                net = cbn.get_network_by_index(attr.network_index)
                vals = attr.l_states[0].l_variable_values
                if isinstance(vals, str):
                    vals = [int(c) for c in vals]
                for i, v_idx in enumerate(net.internal_variables):
                    global_state[f"var_{v_idx}"] = int(vals[i])

        sorted_state = {
            k: global_state[k]
            for k in sorted(global_state.keys(), key=lambda x: int(x.split("_")[1]))
        }
        field_data["global_state_unpacked"].append(sorted_state)
        output_object["pipeline_execution"]["step_3_global_fields"][
            "attractor_fields"
        ].append(field_data)

    with open(output_path, "w") as f:
        json.dump(output_object, f, indent=4)

    print(
        f"[OK] Python simulation completed in {total_ms:.2f} ms. Results saved to {output_path}"
    )


if __name__ == "__main__":
    main()
