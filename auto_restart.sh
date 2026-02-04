#!/bin/bash

echo "==========================================="
echo "Auto-restart Script for SAT Competition"
echo "==========================================="
echo "Este script se reiniciará automáticamente"
echo "si se detiene por cualquier razón."
echo "Presiona Ctrl+C dos veces para detener."
echo "==========================================="
echo ""

while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando ejecución..."
    ./run_sat_competition_resilient.sh
    
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo ""
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ Todos los benchmarks completados!"
        break
    else
        echo ""
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠ Ejecución interrumpida. Reiniciando en 10 segundos..."
        sleep 10
    fi
done

echo ""
echo "Ejecución finalizada completamente."
