# SCMBN Toolkit

Tools for generating, running, and comparing experiments with stationary-coupled
modular Boolean networks (SC-MBNs). The C++ engine is included as a Git submodule
at `lib/scmbn-core`; this repository contains the Python scripts and example data.

## Requirements

- Git with submodule support.
- CMake 3.10 or later and a C++17 compiler.
- OpenMP and the MiniSat development library, required by `scmbn-core`.
- Python 3 for the Python generators and orchestrators.

OpenMP and MiniSat installation depends on your Linux distribution. On Windows
or macOS, configure a compiler with OpenMP support and install MiniSat as well.

## Clone and build

Clone the repository and initialize its submodule:

```bash
git clone --recurse-submodules https://github.com/crptcusco/scmbn-toolkit.git
cd scmbn-toolkit
```

If you already cloned the repository without `--recurse-submodules`:

```bash
git submodule update --init --recursive
```

Configure and build the C++ engine:

```bash
cmake -S lib/scmbn-core -B lib/scmbn-core/build -DCMAKE_BUILD_TYPE=Release
cmake --build lib/scmbn-core/build --parallel
```

The executables are created in `lib/scmbn-core/build/`.

## Run the tests

From the repository root:

```bash
ctest --test-dir lib/scmbn-core/build --output-on-failure
```

This runs the C++ tests registered with CTest. Currently, the test suite
includes `CoreLogicValidation` (`unit_tests`). Python parity validation and
benchmark scripts are not integrated with CTest.

## Run an example

After building the engine, run the pipeline on an example topology tracked in
the repository:

```bash
lib/scmbn-core/build/run_pipeline \
  data_drosophila_update/drosophila_update.json
```

The executable prints JSON to the terminal with the status, metrics, and counts
of attractors, compatible pairs, and fields. The example topology is a
relatively large biological model, so this run may take considerably longer
than the unit tests.

The `src/generators/main_gerador.py` script creates experiment configurations.
For example:

```bash
python3 src/generators/main_gerador.py \
  --output /tmp/scmbn-config.json \
  --networks 4 \
  --vars 6 \
  --seed 42
```

The generated experiment configuration is not in the same format as the
topology JSON consumed by `run_pipeline`.

## Python scripts

There is currently no Python dependency manifest in the repository root.
Some legacy scripts import the `cbnetwork` package, which is not included or
configured by this repository. Therefore, the Python orchestrators and parity
comparisons cannot be assumed to work with Python 3 alone. Check each script's
requirements before running it.

## Repository structure

```text
.
├── data_drosophila_clasic/   # Topology and results for the classical model
├── data_drosophila_update/   # Topology and results for the updated model
├── lib/scmbn-core/           # C++ engine (Git submodule)
└── src/
    ├── generators/           # Network and configuration generators
    ├── legacy/               # Earlier solvers and validators
    └── orchestrators/        # Experiment and benchmark orchestration
```
