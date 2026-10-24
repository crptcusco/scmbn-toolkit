import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "experiments" / "results_t3_n4_v5_s5"


def check_parities():
    print("=== C++ PARITY CHECKER (OPENMP) ===")

    # Validate the 5 samples
    for s in range(1, 6):
        f_trad = DATA_DIR / f"cbn_sample_{s}_Traditional_dynamics.json"
        f_adv = DATA_DIR / f"cbn_sample_{s}_AdvancedParallel_dynamics.json"

        if not f_trad.exists() or not f_adv.exists():
            print(f"[!] Sample {s}: Files not found.")
            continue

        with open(f_trad) as t, open(f_adv) as a:
            data_trad = json.load(t)
            data_adv = json.load(a)

        # Directly compare the attractors found
        if data_trad == data_adv:
            print(f"[OK] Sample {s}: Identical parity. The parallel engine is exact.")
        else:
            print(f"[FAIL] Sample {s}: State divergence between algorithms!")


if __name__ == "__main__":
    check_parities()
