import json
import argparse
import sys
from pathlib import Path
from typing import Any, Dict

def validar_esquema(config: Dict[str, Any]) -> bool:
    required_keys = [
        "n_networks", "v_topology", "n_var_network",
        "n_input_variables", "n_output_variables",
        "connectivity_density", "coupling_type"
    ]
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        print(f"Error: Faltan las siguientes llaves en la configuración: {missing_keys}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="Generador de configuraciones CBN (Source of Truth)")
    
    # Argumentos de Archivo y Mapeo estadístico
    parser.add_argument("--output", type=str, default="config.json", help="Ruta del archivo de salida")
    parser.add_argument("--name", type=str, default="exp_custom", help="Nombre del experimento")
    parser.add_argument("--samples", type=int, default=1, help="Número de muestras independientes a generar")
    
    # Argumentos Topológicos y Dinámicos
    parser.add_argument("--networks", type=int, default=4, help="Número de redes (n_networks)")
    parser.add_argument("--topology", type=int, default=4, help="Tipo de topología (v_topology)")
    parser.add_argument("--vars", type=int, default=6, help="Variables por red (n_var_network)")
    parser.add_argument("--inputs", type=int, default=2, help="Variables de entrada (n_input_variables)")
    parser.add_argument("--outputs", type=int, default=2, help="Variables de salida (n_output_variables)")
    parser.add_argument("--density", type=float, default=0.3, help="Densidad de conectividad (connectivity_density)")
    parser.add_argument("--coupling", type=str, default="NONE", choices=["NONE", "OR", "XOR", "AND", "IDENTITY"], help="Tipo de acoplamiento")
    parser.add_argument("--seed", type=int, default=42, help="Semilla aleatoria base")
    parser.add_argument("--variable-names", type=str, default=None, help="Lista de nombres de variables separados por coma")
    
    # Argumento para modo batch predefinido
    parser.add_argument("--batch", action="store_true", help="Generar un batch automático de exploración")

    args = parser.parse_args()

    configs = []

    var_names = None
    if args.variable_names:
        var_names = [name.strip() for name in args.variable_names.split(",")]
    
    if args.batch:
        # Modo batch: ignora los argumentos individuales y crea la malla de exploración
        tipos_acoplamiento = ["NONE", "XOR", "OR"]
        num_vars = [5, 6, 7]
        for acoplamiento in tipos_acoplamiento:
            for vars_red in num_vars:
                v_names = var_names
                if v_names is None:
                    v_names = [f"Var_{idx}" for idx in range(vars_red)]
                elif len(v_names) < vars_red:
                    v_names = v_names + [f"Var_{idx}" for idx in range(len(v_names), vars_red)]
                else:
                    v_names = v_names[:vars_red]

                configs.append({
                    "experiment_name": f"{args.name}_v{vars_red}_c{acoplamiento}",
                    "n_networks": 4,
                    "v_topology": 4,
                    "n_var_network": vars_red,
                    "n_input_variables": 2,
                    "n_output_variables": 2,
                    "connectivity_density": 0.3,
                    "coupling_type": acoplamiento,
                    "seed": args.seed,
                    "variable_names": v_names
                })
    else:
        # Modo Custom: Genera N muestras distribuidas estadísticamente
        for i in range(1, args.samples + 1):
            v_names = var_names
            if v_names is None:
                v_names = [f"Var_{idx}" for idx in range(args.vars)]
            elif len(v_names) < args.vars:
                v_names = v_names + [f"Var_{idx}" for idx in range(len(v_names), args.vars)]
            else:
                v_names = v_names[:args.vars]

            configs.append({
                "experiment_name": f"{args.name}_s{i:03d}" if args.samples > 1 else args.name,
                "n_networks": args.networks,
                "v_topology": args.topology,
                "n_var_network": args.vars,
                "n_input_variables": args.inputs,
                "n_output_variables": args.outputs,
                "connectivity_density": args.density,
                "coupling_type": args.coupling,
                "seed": args.seed + i,  # Desplazamiento de semilla por muestra
                "variable_names": v_names
            })

    # Validar
    for cfg in configs:
        if not validar_esquema(cfg):
            sys.exit(1)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(configs, f, indent=4)

    print(f"Configuración generada exitosamente en {output_path} ({len(configs)} experimentos/muestras)")

if __name__ == "__main__":
    main()
