#!/bin/bash

# ==============================================================================
# MASSIVE BENCHMARK AUTOMATION SCRIPT
# Scales Coupled Boolean Networks (CBNs) exponentially and safely halts on error.
# ==============================================================================

# 0. Iniciar bitácora permanente (Master Log)
# Todo el output de la terminal se guardará simultáneamente en 'benchmark_master.log'
exec > >(tee -i benchmark_master.log) 2>&1

# Definir la progresión geométrica de las redes locales a evaluar
NETWORKS=(3 4 5 6 7 8 9 10 11 12 13 14 15)
SAMPLES=250

# Inicializar archivo de resumen general de memoria (CSV)
SUMMARY_CSV="benchmark_summary.csv"
echo "N_BNs,Max_RAM_KB,Exit_Code" > "$SUMMARY_CSV"

echo "================================================================="
echo " 🚀 INICIANDO BATCH DE EXPERIMENTOS MASIVOS (${NETWORKS[0]} a ${NETWORKS[-1]} BNs)"
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
    TIME_LOG="${DIR_NAME}/time_profiling.log"

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
    
    # Envolver la ejecución con /usr/bin/time para extraer telemetría real del kernel
    /usr/bin/time -v -o "$TIME_LOG" python3 main_processor_cpp_adv.py --config "$JSON_FILE" --output "$OUT_CSV"
    PROCESSOR_EXIT_CODE=$?

    # Extraer el pico de memoria desde el log de 'time' (Maximum resident set size)
    MAX_RAM=$(grep "Maximum resident set size" "$TIME_LOG" | awk '{print $6}')
    
    # Registrar en el CSV resumen
    echo "$N,$MAX_RAM,$PROCESSOR_EXIT_CODE" >> "$SUMMARY_CSV"
    echo "📊 Pico de memoria (Kernel): $MAX_RAM KB reportados."

    # Interceptar el código de salida del procesador (Ej. Señal 137 OOM Killer / Signal 139 SegFault)
    if [ $PROCESSOR_EXIT_CODE -ne 0 ]; then
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
echo " 🎉 SIMULACIÓN ÉPICA COMPLETADA: ¡EL SISTEMA ESCALÓ A ${NETWORKS[-1]} BNs!"
echo "================================================================="