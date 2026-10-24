#!/bin/bash

# ==============================================================================
# MASSIVE BENCHMARK AUTOMATION SCRIPT
# Scales Coupled Boolean Networks (CBNs) exponentially and safely halts on error.
# ==============================================================================

# Define the geometric progression of local networks to evaluate
NETWORKS=(16 32 64 128 256 512 1024)
SAMPLES=250

echo "================================================================="
echo " 🚀 STARTING MASSIVE EXPERIMENT BATCH (16 to 1024 BNs)"
echo "================================================================="

for N in "${NETWORKS[@]}"; do
    echo ""
    echo "-----------------------------------------------------------------"
    echo " 🔥 EVALUATING SCALABILITY: $N LOCAL NETWORKS (BNs)"
    echo "-----------------------------------------------------------------"

    # 1. Create an isolated directory to keep artifacts organized
    DIR_NAME="benchmark_BN_${N}"
    mkdir -p "$DIR_NAME"
    echo "📁 Working directory: $DIR_NAME"

    # 2. Define a strict file naming convention
    EXP_NAME="aleatory_fixed_2_${N}_5_2_${SAMPLES}"
    JSON_FILE="${DIR_NAME}/${EXP_NAME}.json"
    OUT_CSV="${DIR_NAME}/exp_${EXP_NAME}"

    # 3. Generation phase
    echo "⏳ [1/2] Generating a dataset of $SAMPLES samples for $N BNs..."
    python3 main_gerador.py \
        --output "$JSON_FILE" \
        --name "$EXP_NAME" \
        --topology 2 \
        --networks "$N" \
        --vars 5 \
        --inputs 2 \
        --outputs 2 \
        --density 0.5 \
        --coupling OR \
        --seed 42 \
        --samples "$SAMPLES"

    # Check the generator's exit code
    if [ $? -ne 0 ]; then
        echo "❌ FATAL ERROR: Generator failed at $N BNs."
        echo "🛑 Batch stopped to prevent data corruption."
        exit 1
    fi

    # 4. Processing phase (the actual stress test)
    echo "🧠 [2/2] Processing the topology of $N BNs (C++ only)..."
    python3 main_processor_cpp_adv.py --config "$JSON_FILE" --output "$OUT_CSV"

    # Check the processor's exit code (e.g. signal 137 OOM killer / signal 139 segfault)
    if [ $? -ne 0 ]; then
        echo ""
        echo "================================================================="
        echo " 🚨 EXPERIMENT STOPPED AT: $N LOCAL NETWORKS (BNs) 🚨"
        echo "================================================================="
        echo "Probable cause: The operating system killed the process due to"
        echo "a memory overflow while computing the massive attractor fields"
        echo "generated in Step 3."
        echo "Check 'dmesg -T | tail -n 20' to confirm kernel intervention."
        exit 1
    fi

    echo "✅ SUCCESS: Experiment with $N BNs completed."
done

echo ""
echo "================================================================="
echo " 🎉 MASSIVE SIMULATION COMPLETE: THE SYSTEM SCALED TO 1024 BNs!"
echo "================================================================="