import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "experiments" / "results_t3_n4_v5_s5"


def check_parities():
    print("=== VERIFICADOR DE PARIDAD C++ (OPENMP) ===")

    # Validar las 5 muestras
    for s in range(1, 6):
        f_trad = DATA_DIR / f"cbn_sample_{s}_Traditional_dynamics.json"
        f_adv = DATA_DIR / f"cbn_sample_{s}_AdvancedParallel_dynamics.json"

        if not f_trad.exists() or not f_adv.exists():
            print(f"[!] Muestra {s}: Archivos no encontrados.")
            continue

        with open(f_trad) as t, open(f_adv) as a:
            data_trad = json.load(t)
            data_adv = json.load(a)

        # Comparación directa de los atractores hallados
        if data_trad == data_adv:
            print(f"[OK] Muestra {s}: Paridad idéntica. El motor paralelo es exacto.")
        else:
            print(f"[FAIL] Muestra {s}: ¡Divergencia de estados entre algoritmos!")


if __name__ == "__main__":
    check_parities()
