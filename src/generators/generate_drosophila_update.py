import json
import os

def get_updated_neurogenic_logic():
    """
    Conjunctive Normal Form (CNF) equations including the classical core (1-13)
    plus the temporal progression module (14: Imp, 15: Syp, 16: E93) based on recent 2024 literature.
    """
    return [
        # --- CLASSICAL CORE (1 - 13) ---
        {"index": 1, "cnf": [[1, -17], [-1, 17]]},  # Notch_intra depends on Notch/Delta_Input (Var 17)
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
        {"index": 13, "cnf": [[13, -11], [-13, 11]]},  # Delta (Output)
        
        # --- TEMPORAL PROGRESSION MODULE (14 - 16) ---
        {"index": 14, "cnf": [[-1, 14], [1, -14]]},    # Imp is activated by Notch_intra
        {"index": 15, "cnf": [[-14, 15], [14, -15]]},  # Syp is regulated by Imp
        {"index": 16, "cnf": [[-15, 16], [15, -16]]}   # E93 mediates lineage progression
    ]

def get_updated_biological_names():
    return [
        "Notch_intra", "SU(H)/Notch_intra", "espl", "ESPL", "ac", "sc", 
        "AC", "SC", "ACDA", "SCDA", "dl", "SUH", "Delta", 
        "Imp", "Syp", "E93", "Notch/Delta_Input"
    ]

def main():
    topology = {
        "local_networks": [],
        "directed_edges": []
    }

    # 1. Create the 7 cells (modules) of the proneural cluster with 17 variables
    for i in range(1, 8):
        topology["local_networks"].append({
            "index": i,
            "internal_variables": list(range(1, 18)),
            "variable_names": get_updated_biological_names(),
            "logic": get_updated_neurogenic_logic()
        })

    # 2. Couplings (6 neighboring cells pointing to the central cell 1 with Threshold >= 4)
    edge_idx = 1
    for neighbor_id in range(2, 8): 
        topology["directed_edges"].append({
            "index": edge_idx,
            "source": neighbor_id,
            "target": 1,
            "signal_var": 17,
            "output_vars": [13],
            "function": "Threshold", 
            "true_table": {
                "0": "0",
                "1": "1"
            }
        })
        edge_idx += 1

    # 3. Save JSON output explicitly targeting 'drosophila_update.json'
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "data"))
    os.makedirs(data_dir, exist_ok=True)
    output_path = os.path.join(data_dir, "drosophila_update.json")
    
    with open(output_path, "w") as f:
        json.dump(topology, f, indent=4)
        print(f"✅ Updated Drosophila topology successfully generated at:\n{output_path}")

if __name__ == "__main__":
    main()