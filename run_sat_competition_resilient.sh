#!/bin/bash

# ============================================
# SAT Competition 2024 - Ordenado por Tamaño
# ============================================

SOLVER="./minisat/simp/minisat"
BENCHMARKS_DIR="./benchmarks"
RESULTS_DIR="./resultados"

# Parámetros oficiales SAT-COMP 2024
TIMEOUT=5000
MEMORY_LIMIT_MB=7000
PARALLEL_JOBS=3

# Archivos de control
mkdir -p "$RESULTS_DIR/logs"
mkdir -p "$RESULTS_DIR/raw_output"
SUMMARY_CSV="$RESULTS_DIR/results_complete.csv"
COMPLETED_FILE="$RESULTS_DIR/.completed_benchmarks"
LOCK_FILE="$RESULTS_DIR/.execution_lock"
PROGRESS_FILE="$RESULTS_DIR/.progress"

# Crear CSV con TODAS las métricas si no existe
if [ ! -f "$SUMMARY_CSV" ]; then
    cat > "$SUMMARY_CSV" << 'CSVHEADER'
benchmark,result,exit_code,cpu_time_seconds,system_time_seconds,wall_time_seconds,cpu_percentage,max_memory_kb,avg_memory_kb,major_page_faults,minor_page_faults,voluntary_context_switches,involuntary_context_switches,file_system_inputs,file_system_outputs,socket_messages_sent,socket_messages_received,signals_delivered,page_size_bytes,conflicts,decisions,propagations,restarts,conflict_literals,learnt_literals,max_literals,tot_literals,variables,clauses,original_clauses,learned_clauses_deleted,avg_clause_length,conflicts_per_second,decisions_per_second,propagations_per_second,random_decisions_percentage,preprocessing_time,solving_time,total_literals_in_learned,deleted_literals_percentage,file_size_bytes
CSVHEADER
fi

touch "$COMPLETED_FILE"
echo "0" > "$PROGRESS_FILE"

# Función para extraer valor numérico de forma segura
extract_value() {
    local pattern="$1"
    local file="$2"
    local default="${3:-0}"
    
    value=$(grep "$pattern" "$file" 2>/dev/null | grep -oP '\d+\.?\d*' | head -1)
    echo "${value:-$default}"
}

# Función para procesar un benchmark
process_benchmark() {
    cnf_file="$1"
    basename=$(basename "$cnf_file" .cnf)
    file_size=$(stat -f%z "$cnf_file" 2>/dev/null || stat -c%s "$cnf_file" 2>/dev/null || echo "0")
    
    # Verificar si ya fue procesado
    if grep -q "^${basename}$" "$COMPLETED_FILE" 2>/dev/null; then
        echo "[SKIP] $basename (ya procesado)"
        return 0
    fi
    
    log_file="$RESULTS_DIR/logs/${basename}.log"
    raw_file="$RESULTS_DIR/raw_output/${basename}.out"
    
    # Actualizar progreso
    current=$(cat "$PROGRESS_FILE")
    new_progress=$((current + 1))
    echo "$new_progress" > "$PROGRESS_FILE"
    
    file_size_kb=$(echo "scale=2; $file_size / 1024" | bc 2>/dev/null || echo "0")
    echo "[$(date '+%H:%M:%S')] [$new_progress/400] INICIO: $basename (${file_size_kb} KB)"
    
    # Ejecutar solver con métricas completas
    {
        echo "c ============================================"
        echo "c SAT Competition 2024 - Benchmark Execution"
        echo "c ============================================"
        echo "c Benchmark: $basename"
        echo "c Input file: $cnf_file"
        echo "c File size: $file_size bytes"
        echo "c Solver: MiniSat 2.2.0 (simp)"
        echo "c Timeout: $TIMEOUT seconds"
        echo "c Memory limit: $MEMORY_LIMIT_MB MB"
        echo "c Started: $(date '+%Y-%m-%d %H:%M:%S.%N')"
        echo "c System: $(uname -a)"
        echo "c ============================================"
        echo ""
        
        start_time=$(date +%s.%N)
        start_epoch=$(date +%s)
        
        /usr/bin/time -v timeout ${TIMEOUT}s bash -c "ulimit -v $((MEMORY_LIMIT_MB * 1024)) 2>/dev/null; exec '$SOLVER' '$cnf_file'" 2>&1
        
        exit_code=$?
        end_time=$(date +%s.%N)
        end_epoch=$(date +%s)
        wall_time=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")
        
        echo ""
        echo "c ============================================"
        echo "c Execution Summary"
        echo "c ============================================"
        echo "c Exit code: $exit_code"
        echo "c Wall time: $wall_time seconds"
        echo "c Start epoch: $start_epoch"
        echo "c End epoch: $end_epoch"
        
        if [ $exit_code -eq 10 ]; then
            result="SAT"
            echo "s SATISFIABLE"
        elif [ $exit_code -eq 20 ]; then
            result="UNSAT"
            echo "s UNSATISFIABLE"
        elif [ $exit_code -eq 124 ]; then
            result="TIMEOUT"
            echo "s UNKNOWN"
            echo "c Reason: Timeout after $TIMEOUT seconds"
        elif [ $exit_code -eq 137 ] || [ $exit_code -eq 139 ]; then
            result="MEMOUT"
            echo "s UNKNOWN"
            echo "c Reason: Memory limit exceeded"
        else
            result="ERROR"
            echo "s UNKNOWN"
            echo "c Reason: Solver error (exit code $exit_code)"
        fi
        
        echo "c Result: $result"
        echo "c Completed: $(date '+%Y-%m-%d %H:%M:%S.%N')"
        echo "c ============================================"
        
    } > "$raw_file" 2>&1
    
    cp "$raw_file" "$log_file"
    
    # Extraer métricas
    cpu_time=$(extract_value "User time \(seconds\):" "$raw_file" "0")
    system_time=$(extract_value "System time \(seconds\):" "$raw_file" "0")
    cpu_percent=$(extract_value "Percent of CPU this job got:" "$raw_file" "0")
    max_memory_kb=$(extract_value "Maximum resident set size \(kbytes\):" "$raw_file" "0")
    avg_memory_kb=$(extract_value "Average resident set size \(kbytes\):" "$raw_file" "0")
    major_faults=$(extract_value "Major \(requiring I/O\) page faults:" "$raw_file" "0")
    minor_faults=$(extract_value "Minor \(reclaiming a frame\) page faults:" "$raw_file" "0")
    voluntary_switches=$(extract_value "Voluntary context switches:" "$raw_file" "0")
    involuntary_switches=$(extract_value "Involuntary context switches:" "$raw_file" "0")
    fs_inputs=$(extract_value "File system inputs:" "$raw_file" "0")
    fs_outputs=$(extract_value "File system outputs:" "$raw_file" "0")
    socket_sent=$(extract_value "Socket messages sent:" "$raw_file" "0")
    socket_received=$(extract_value "Socket messages received:" "$raw_file" "0")
    signals=$(extract_value "Signals delivered:" "$raw_file" "0")
    page_size=$(extract_value "Page size \(bytes\):" "$raw_file" "4096")
    
    variables=$(extract_value "Number of variables:" "$raw_file" "0")
    clauses=$(extract_value "Number of clauses:" "$raw_file" "0")
    conflicts=$(grep "^conflicts" "$raw_file" | grep -oP ':\s*\K[\d]+' | head -1 || echo "0")
    decisions=$(grep "^decisions" "$raw_file" | grep -oP ':\s*\K[\d]+' | head -1 || echo "0")
    propagations=$(grep "^propagations" "$raw_file" | grep -oP ':\s*\K[\d]+' | head -1 || echo "0")
    restarts=$(grep "^restarts" "$raw_file" | grep -oP ':\s*\K[\d]+' | head -1 || echo "0")
    conflict_literals=$(grep "^conflict literals" "$raw_file" | grep -oP ':\s*\K[\d]+' | head -1 || echo "0")
    tot_literals=$(grep "^conflict literals" "$raw_file" | grep -oP ':\s*\K[\d]+' | head -1 || echo "0")
    max_literals=$(grep "max_literals" "$raw_file" | grep -oP '\d+' | head -1 || echo "0")
    deleted_percentage=$(grep "conflict literals" "$raw_file" | grep -oP '\([\d.]+\s*%' | grep -oP '[\d.]+' | head -1 || echo "0")
    
    if [ "$wall_time" != "0" ] && [ "$(echo "$wall_time > 0" | bc -l 2>/dev/null)" = "1" ]; then
        conflicts_per_sec=$(echo "scale=2; $conflicts / $wall_time" | bc -l 2>/dev/null || echo "0")
        decisions_per_sec=$(echo "scale=2; $decisions / $wall_time" | bc -l 2>/dev/null || echo "0")
        propagations_per_sec=$(echo "scale=2; $propagations / $wall_time" | bc -l 2>/dev/null || echo "0")
    else
        conflicts_per_sec="0"
        decisions_per_sec="0"
        propagations_per_sec="0"
    fi
    
    random_decisions=$(grep "decisions" "$raw_file" | grep -oP '\([\d.]+\s*%' | grep -oP '[\d.]+' | head -1 || echo "0")
    
    if [ "$clauses" != "0" ]; then
        avg_clause_length=$(echo "scale=2; ($variables * 2) / $clauses" | bc -l 2>/dev/null || echo "0")
    else
        avg_clause_length="0"
    fi
    
    original_clauses="$clauses"
    learned_clauses_deleted="$deleted_percentage"
    preprocessing_time=$(grep "pre-processing time" "$raw_file" | grep -oP '[\d.]+' | head -1 || echo "0")
    solving_time=$(echo "$cpu_time - $preprocessing_time" | bc -l 2>/dev/null || echo "$cpu_time")
    learnt_literals="$tot_literals"
    
    # Guardar en CSV con lock
    (
        flock -x 200
        echo "$basename,$result,$exit_code,$cpu_time,$system_time,$wall_time,$cpu_percent,$max_memory_kb,$avg_memory_kb,$major_faults,$minor_faults,$voluntary_switches,$involuntary_switches,$fs_inputs,$fs_outputs,$socket_sent,$socket_received,$signals,$page_size,$conflicts,$decisions,$propagations,$restarts,$conflict_literals,$learnt_literals,$max_literals,$tot_literals,$variables,$clauses,$original_clauses,$learned_clauses_deleted,$avg_clause_length,$conflicts_per_sec,$decisions_per_sec,$propagations_per_sec,$random_decisions,$preprocessing_time,$solving_time,$tot_literals,$deleted_percentage,$file_size" >> "$SUMMARY_CSV"
        echo "$basename" >> "$COMPLETED_FILE"
    ) 200>"$LOCK_FILE"
    
    echo "[$(date '+%H:%M:%S')] ✓ [$new_progress/400] $basename -> $result (CPU: ${cpu_time}s, Mem: ${max_memory_kb}KB)"
}

export -f process_benchmark extract_value
export SOLVER RESULTS_DIR TIMEOUT MEMORY_LIMIT_MB SUMMARY_CSV COMPLETED_FILE LOCK_FILE PROGRESS_FILE

# ============================================
# Inicio de ejecución
# ============================================

total=$(find "$BENCHMARKS_DIR" -name "*.cnf" | wc -l)
completed=$(wc -l < "$COMPLETED_FILE" 2>/dev/null || echo "0")
remaining=$((total - completed))

echo "============================================"
echo "SAT Competition 2024 - Ordenado por Tamaño"
echo "============================================"
echo "Configuración:"
echo "  Total benchmarks: $total"
echo "  Ya completados: $completed"
echo "  Restantes: $remaining"
echo "  Parallel jobs: $PARALLEL_JOBS"
echo "  Timeout: ${TIMEOUT}s (83.3 min)"
echo "  Orden: Menor a mayor tamaño de archivo"
echo "============================================"
echo ""

if [ $remaining -eq 0 ]; then
    echo "¡Todos los benchmarks ya fueron procesados!"
    exit 0
fi

echo "Ordenando benchmarks por tamaño..."
echo ""

# Ejecutar en paralelo ORDENADO POR TAMAÑO (menor a mayor)
find "$BENCHMARKS_DIR" -name "*.cnf" -exec ls -lS {} \; | awk '{print $NF}' | tac | while read cnf_file; do
    basename=$(basename "$cnf_file" .cnf)
    if ! grep -q "^${basename}$" "$COMPLETED_FILE" 2>/dev/null; then
        echo "$cnf_file"
    fi
done | xargs -P $PARALLEL_JOBS -I {} bash -c 'process_benchmark "{}"'

echo ""
echo "============================================"
echo "Ejecución Completada"
echo "============================================"

completed_now=$(wc -l < "$COMPLETED_FILE")
sat_count=$(grep -c ",SAT," "$SUMMARY_CSV" 2>/dev/null || echo "0")
unsat_count=$(grep -c ",UNSAT," "$SUMMARY_CSV" 2>/dev/null || echo "0")
timeout_count=$(grep -c ",TIMEOUT," "$SUMMARY_CSV" 2>/dev/null || echo "0")
memout_count=$(grep -c ",MEMOUT," "$SUMMARY_CSV" 2>/dev/null || echo "0")

echo "Procesados: $completed_now / $total"
echo "  SAT: $sat_count"
echo "  UNSAT: $unsat_count"
echo "  TIMEOUT: $timeout_count"
echo "  MEMOUT: $memout_count"
echo ""
echo "CSV completo: $SUMMARY_CSV"
echo "============================================"
