#!/bin/bash
# filepath: e:\Universidad\Tesis\monitor.sh

while true; do
    clear
    
    # Variables con validación
    COMPLETED=$(wc -l < resultados/.completed_benchmarks 2>/dev/null || echo 0)
    TOTAL=400
    PERCENT=$(awk "BEGIN {printf \"%.1f\", ($COMPLETED/$TOTAL)*100}" 2>/dev/null || echo "0.0")
    
    SAT=$(grep -c ",SAT," resultados/results_complete.csv 2>/dev/null || echo 0)
    UNSAT=$(grep -c ",UNSAT," resultados/results_complete.csv 2>/dev/null || echo 0)
    TIMEOUT=$(grep -c ",TIMEOUT," resultados/results_complete.csv 2>/dev/null || echo 0)
    MEMOUT=$(grep -c ",MEMOUT," resultados/results_complete.csv 2>/dev/null || echo 0)
    ERROR=$(grep -c ",ERROR," resultados/results_complete.csv 2>/dev/null || echo 0)
    
    PROCS=$(ps aux | grep -E "minisat|run_sat" | grep -v grep | wc -l)
    RAM=$(free -h | grep Mem: | awk '{print $3 " / " $2}')
    
    # Header con color
    echo -e "\e[1;36m╔════════════════════════════════════════════════════════════╗\e[0m"
    echo -e "\e[1;36m║    MINISAT - EJECUCIÓN ORDENADA POR TAMAÑO (menor→mayor)  ║\e[0m"
    echo -e "\e[1;36m╠════════════════════════════════════════════════════════════╣\e[0m"
    
    # Progreso con barra
    printf "\e[1;37m║  Progreso: \e[1;33m%3d / %3d\e[0m  (\e[1;32m%5.1f%%\e[0m)                          \e[1;37m║\e[0m\n" $COMPLETED $TOTAL $PERCENT
    
    # Barra de progreso
    FILLED=$(awk "BEGIN {printf \"%d\", ($COMPLETED/$TOTAL)*50}" 2>/dev/null || echo 0)
    printf "\e[1;37m║  [\e[1;32m"
    for i in $(seq 1 $FILLED); do printf "█"; done
    printf "\e[1;30m"
    for i in $(seq $((FILLED+1)) 50); do printf "░"; done
    printf "\e[1;37m]  ║\e[0m\n"
    
    printf "\e[1;37m║  Procesos activos: \e[1;33m%2d\e[1;37m                                    ║\e[0m\n" $PROCS
    
    echo -e "\e[1;36m╠════════════════════════════════════════════════════════════╣\e[0m"
    echo -e "\e[1;37m║  RESULTADOS:                                               ║\e[0m"
    printf "\e[1;37m║    \e[1;32mSAT:     \e[1;37m%4d\e[0m                                           \e[1;37m║\e[0m\n" $SAT
    printf "\e[1;37m║    \e[1;34mUNSAT:   \e[1;37m%4d\e[0m                                           \e[1;37m║\e[0m\n" $UNSAT
    printf "\e[1;37m║    \e[1;33mTIMEOUT: \e[1;37m%4d\e[0m                                           \e[1;37m║\e[0m\n" $TIMEOUT
    printf "\e[1;37m║    \e[1;31mMEMOUT:  \e[1;37m%4d\e[0m                                           \e[1;37m║\e[0m\n" $MEMOUT
    printf "\e[1;37m║    \e[1;35mERROR:   \e[1;37m%4d\e[0m                                           \e[1;37m║\e[0m\n" $ERROR
    
    echo -e "\e[1;36m╠════════════════════════════════════════════════════════════╣\e[0m"
    printf "\e[1;37m║  RAM: \e[1;35m%-48s\e[1;37m ║\e[0m\n" "$RAM"
    
    echo -e "\e[1;36m╠════════════════════════════════════════════════════════════╣\e[0m"
    echo -e "\e[1;37m║  ÚLTIMAS 5 COMPLETADAS:                                    ║\e[0m"
    
    tail -5 resultados/.completed_benchmarks 2>/dev/null | while read line; do
        SHORT="${line:0:56}"
        printf "\e[1;37m║  \e[0;32m%-56s\e[1;37m ║\e[0m\n" "$SHORT"
    done
    
    echo -e "\e[1;36m╚════════════════════════════════════════════════════════════╝\e[0m"
    echo -e "\e[0;90m  Actualización cada 5 segundos... (Ctrl+C para salir)\e[0m"
    
    sleep 5
done