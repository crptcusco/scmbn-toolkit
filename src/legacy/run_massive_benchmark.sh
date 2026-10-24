#!/bin/bash

# ==============================================================================
# MASSIVE BENCHMARK AUTOMATION SCRIPT
# Scales Coupled Boolean Networks (CBNs) exponentially and safely halts on error.
# ==============================================================================

# Definir la progresión geométrica de las redes locales a evaluar
NETWORKS=(16 32 64 128 256 512 1024)
SAMPLES=250

echo "================================================================="
echo " 🚀 INICIANDO BATCH DE EXPERIMENTOS MASIVOS (16 a 1024 BNs)"
echo "================================================================="

for N in "${NETWORKS[@]}"; do
    echo ""
    echo "-----------------------------------------------------------------"
    echo " 🔥 EVALUANDO ESCALABILIDAD: $N REDES LOCALES (BNs)"
    echo "-----------------------------------------------------------------"

    # 1. Crear un directorio aislado para mantener el orden de los artefactos
    DIR_NAME="benchmark_BN_${N}"
    mkdir -p "$DIR_NAME"
    echo "📁 Directorio de trabajo: $DIR_NAME"

    # 2. Definir nomenclatura estricta de archivos
    EXP_NAME="aleatory_fixed_2_${N}_5_2_${SAMPLES}"
    JSON_FILE="${DIR_NAME}/${EXP_NAME}.json"
    OUT_CSV="${DIR_NAME}/exp_${EXP_NAME}"

    # 3. Fase de Generación
    echo "⏳ [1/2] Generando dataset de $SAMPLES muestras para $N BNs..."
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

    # Interceptar el código de salida (exit code) del generador
    if [ $? -ne 0 ]; then
        echo "❌ ERROR FATAL: El generador falló en $N BNs."
        echo "🛑 Ejecución del batch detenida para evitar corrupción de datos."
        exit 1
    fi

    # 4. Fase de Procesamiento (El verdadero test de estrés)
    echo "🧠 [2/2] Procesando la topología de $N BNs (C++ Exclusivo)..."
    python3 main_processor_cpp_adv.py --config "$JSON_FILE" --output "$OUT_CSV"

    # Interceptar el código de salida del procesador (Ej. Señal 137 OOM Killer / Signal 139 SegFault)
    if [ $? -ne 0 ]; then
        echo ""
        echo "================================================================="
        echo " 🚨 EXPERIMENTO DETENIDO EN: $N REDES LOCALES (BNs) 🚨"
        echo "================================================================="
        echo "Motivo probable: El sistema operativo aniquiló el proceso debido a"
        echo "un desbordamiento de memoria (Memory Overflow) al intentar computar"
        echo "los Campos Atractores masivos generados en el Paso 3."
        echo "Revisa 'dmesg -T | tail -n 20' para confirmar la intervención del kernel."
        exit 1
    fi

    echo "✅ ÉXITO: Experimento con $N BNs superado."
done

echo ""
echo "================================================================="
echo " 🎉 SIMULACIÓN ÉPICA COMPLETADA: ¡EL SISTEMA ESCALÓ A 1024 BNs!"
echo "================================================================="