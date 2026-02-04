#!/bin/bash
# filepath: e:\Universidad\Tesis\verify_progres.sh

echo "Verificando integridad de resultados..."

# Contar benchmarks completados
COMPLETED_COUNT=$(wc -l < resultados/.completed_benchmarks 2>/dev/null || echo 0)
CSV_LINES=$(($(wc -l < resultados/results_complete.csv 2>/dev/null || echo 1) - 1))
LOGS_COUNT=$(ls resultados/logs/*.log 2>/dev/null | wc -l)

echo ""
echo "════════════════════════════════════════════════"
echo "  VERIFICACIÓN DE INTEGRIDAD"
echo "════════════════════════════════════════════════"
printf "  .completed_benchmarks:  %4d\n" $COMPLETED_COUNT
printf "  results_complete.csv:   %4d (sin header)\n" $CSV_LINES
printf "  Archivos .log:          %4d\n" $LOGS_COUNT
echo "════════════════════════════════════════════════"

# Actualizar .progress si está desincronizado
if [ "$COMPLETED_COUNT" -gt 0 ]; then
    echo "$COMPLETED_COUNT" > resultados/.progress
    echo "✓ Archivo .progress actualizado a $COMPLETED_COUNT"
fi

# Verificar inconsistencias
if [ "$COMPLETED_COUNT" -ne "$CSV_LINES" ]; then
    echo ""
    echo "⚠️  INCONSISTENCIA DETECTADA:"
    echo "   Diferencia entre .completed_benchmarks ($COMPLETED_COUNT) y CSV ($CSV_LINES)"
    echo ""
    
    # Encontrar benchmarks en completed pero no en CSV
    echo "Buscando discrepancias..."
    
    while read benchmark; do
        if ! grep -q "^$benchmark," resultados/results_complete.csv 2>/dev/null; then
            echo "  - Falta en CSV: $benchmark"
        fi
    done < resultados/.completed_benchmarks
fi

# Mostrar distribución de resultados
echo ""
echo "════════════════════════════════════════════════"
echo "  DISTRIBUCIÓN DE RESULTADOS"
echo "════════════════════════════════════════════════"
printf "  SAT:     %4d\n" $(grep -c ",SAT," resultados/results_complete.csv 2>/dev/null || echo 0)
printf "  UNSAT:   %4d\n" $(grep -c ",UNSAT," resultados/results_complete.csv 2>/dev/null || echo 0)
printf "  TIMEOUT: %4d\n" $(grep -c ",TIMEOUT," resultados/results_complete.csv 2>/dev/null || echo 0)
printf "  MEMOUT:  %4d\n" $(grep -c ",MEMOUT," resultados/results_complete.csv 2>/dev/null || echo 0)
printf "  ERROR:   %4d\n" $(grep -c ",ERROR," resultados/results_complete.csv 2>/dev/null || echo 0)
echo "════════════════════════════════════════════════"

# Estimación de tiempo restante
if [ $COMPLETED_COUNT -gt 0 ]; then
    REMAINING=$((400 - COMPLETED_COUNT))
    
    # Calcular tiempo promedio (en segundos) de benchmarks completados
    AVG_TIME=$(awk -F',' 'NR>1 && $4 != "" {sum+=$4; count++} END {if(count>0) print sum/count; else print 5000}' resultados/results_complete.csv)
    
    # Tiempo restante estimado (con 3 jobs paralelos)
    EST_SECONDS=$(echo "$AVG_TIME * $REMAINING / 3" | bc -l)
    EST_HOURS=$(echo "scale=1; $EST_SECONDS / 3600" | bc -l)
    
    echo ""
    echo "════════════════════════════════════════════════"
    echo "  ESTIMACIÓN DE TIEMPO RESTANTE"
    echo "════════════════════════════════════════════════"
    printf "  Benchmarks restantes:    %4d\n" $REMAINING
    printf "  Tiempo promedio:         %.1f s/benchmark\n" $AVG_TIME
    printf "  Tiempo estimado total:   %.1f horas\n" $EST_HOURS
    echo "════════════════════════════════════════════════"
fi

echo ""
echo "Verificación completa."