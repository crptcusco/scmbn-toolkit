import json
import os

def get_neurogenic_logic():
    """Forma Normal Conjunta de las ecuaciones de transición biológicas."""
    return [
        {"index": 1, "cnf": [[1, -14], [-1, 14]]},
        {"index": 2, "cnf": [[-2, 1], [-2, 12], [-2, -13], [-1, -12, 13, 2]]},
        {"index": 3, "cnf": [[-3, 2], [-3, 9], [-3, 10], [-3, -4], [-2, -9, -10, 4, 3]]},
        {"index": 4, "cnf": [[4, -3], [-4, 3]]},
        {"index": 5, "cnf": [[-5, -4], [-5, -2], [-5, 10], [-5, 9], [4, 2, -10, -9, 5]]},
        {"index": 6, "cnf": [[-6, -4], [-6, -2], [-6, 10], [-6, 9], [4, 2, -10, -9, 6]]},
        {"index": 7, "cnf": [[7, -5], [-7, 5]]},
        {"index": 8, "cnf": [[8, -6], [-8, 6]]},
        {"index": 9, "cnf": [[9, -7], [-9, 7]]},
        {"index": 10, "cnf": [[10, -8], [-10, 8]]},
        {"index": 11, "cnf": [[-11, 9], [-11, 10], [-9, -10, 11]]},
        {"index": 12, "cnf": [[12, -2], [-12, 2]]},
        {"index": 13, "cnf": [[13, -11], [-13, 11]]}
    ]

def get_biological_names():
    return [
        "Notch_intra", "SU(H)/Notch_intra", "espl", "ESPL", "ac", "sc", 
        "AC", "SC", "ACDA", "SCDA", "dl", "SUH", "Delta", "Notch/Delta_Input"
    ]

def main():
    topology = {
        "local_networks": [],
        "directed_edges": []
    }

    # 1. Crear las 7 células (Módulos) del Cluster Proneural
    for i in range(1, 8):
        topology["local_networks"].append({
            "index": i,
            "internal_variables": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
            "variable_names": get_biological_names(),
            "logic": get_neurogenic_logic()
        })

    # 2. Acoplamientos (6 células vecinas hacia la célula central 1)
    edge_idx = 1
    for neighbor_id in range(2, 8): 
        topology["directed_edges"].append({
            "index": edge_idx,
            "source": neighbor_id,
            "target": 1,
            "signal_var": 14,       # La variable que recibe el acoplamiento
            "output_vars": [13],    # Exporta Delta
            "function": "Threshold", # <-- ¡Restaurado a su valor correcto gracias a Jules!
            "true_table": {
                "0": "0",
                "1": "1"
            }
        })
        edge_idx += 1

    # 3. Guardar JSON
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "data"))
    os.makedirs(data_dir, exist_ok=True)
    output_path = os.path.join(data_dir, "drosophila_topology.json")
    
    with open(output_path, "w") as f:
        json.dump(topology, f, indent=4)
        print(f"✅ Topología de Drosophila restaurada con 'Threshold' en:\n{output_path}")

if __name__ == "__main__":
    main()