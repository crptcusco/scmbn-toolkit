import argparse
import random
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).resolve().parents[2] / "cbn_python" / "src"))

from cbnetwork.cbnetwork import CBN  # noqa: E402
from cbnetwork.coupling import CouplingStrategy  # noqa: E402
from cbnetwork.coupling_bitmask import CouplingFactory  # noqa: E402


class BitmaskCouplingStrategy(CouplingStrategy):
    """
    Adapter to use CouplingFunction within the existing CBN generator.
    """

    def __init__(self, coupling_func):
        self.cf = coupling_func
        self.coupling_type = coupling_func.name
        self.bitmask = coupling_func.bitmask

    def generate_coupling_function(self, output_variables: list[int]) -> str:
        if self.cf.name == "OR":
            return " " + " ∨ ".join(map(str, output_variables)) + " "
        elif self.cf.name == "AND":
            return " " + " ∧ ".join(map(str, output_variables)) + " "
        elif self.cf.name == "BUFFER":
            # For buffer, we expect exactly 1 output variable
            var_name = str(output_variables[0]) if output_variables else "0"
            return " " + var_name + " "
        return " " + " ∨ ".join(map(str, output_variables)) + " "

    def to_cnf(
        self, output_variables: list[int], coupling_variable: int
    ) -> list[list[int]]:
        # For parity with C++ which defaults to OR in most cases for CNF,
        # let's stick with OR for now unless it's a known rule.
        clauses = []
        if self.cf.name == "AND":
            # C <=> (V1 & V2 & ...)
            for var in output_variables:
                clauses.append([var, -coupling_variable])
            clauses.append([-v for v in output_variables] + [coupling_variable])
        else:  # Default OR (includes BUFFER k=1)
            for var in output_variables:
                clauses.append([-var, coupling_variable])
            clauses.append(output_variables + [-coupling_variable])
        return clauses


def main():
    parser = argparse.ArgumentParser(description="CBN Topology Generator")
    parser.add_argument("--topology", type=int, default=3, help="Topology type")
    parser.add_argument(
        "--networks", type=int, default=4, help="Number of local networks"
    )
    parser.add_argument("--vars", type=int, default=5, help="Variables per network")
    parser.add_argument("--output", type=str, required=True, help="Output JSON file")

    args = parser.parse_args()

    print(
        f"[*] Generating CBN: Topology={args.topology}, Networks={args.networks}, Vars={args.vars}"
    )

    # Dynamic coupling factory
    def get_dynamic_coupling(k):
        if k == 1:
            return BitmaskCouplingStrategy(CouplingFactory.create_buffer_function())
        else:
            # Randomly choose between standard rules for k > 1
            choice = random.randint(0, 3)
            if choice == 0:
                return BitmaskCouplingStrategy(CouplingFactory.create_or_function(k))
            elif choice == 1:
                return BitmaskCouplingStrategy(CouplingFactory.create_and_function(k))
            elif choice == 2:
                return BitmaskCouplingStrategy(
                    CouplingFactory.create_majority_function(k)
                )
            else:
                return BitmaskCouplingStrategy(
                    CouplingFactory.create_mixed_random_function(k)
                )

    cbn = CBN.cbn_generator(
        v_topology=args.topology,
        n_networks=args.networks,
        n_var_network=args.vars,
        n_input_variables=1,  # This will be overridden by k in the generator
        n_output_variables=1,  # This will be overridden by k in the generator
        coupling_factory=get_dynamic_coupling,
    )

    cbn.to_json(args.output)
    print(f"[OK] Saved to {args.output}")


if __name__ == "__main__":
    main()
