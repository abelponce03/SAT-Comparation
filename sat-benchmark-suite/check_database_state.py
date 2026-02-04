"""
Script para verificar estado de la base de datos
"""

import sys
from pathlib import Path

# FIX: Correct path
sys.path.append(str(Path(__file__).parent))

from app.core.database import DatabaseManager
import pandas as pd

def check_database():
    db = DatabaseManager()
    
    print("=" * 60)
    print("🔍 VERIFICACIÓN DE BASE DE DATOS")
    print("=" * 60)
    
    # 1. Estadísticas generales
    stats = db.get_database_stats()
    
    print("\n📊 ESTADÍSTICAS GENERALES:")
    print(f"  Solvers:      {stats['solvers_count']}")
    print(f"  Benchmarks:   {stats['benchmarks_count']}")
    print(f"  Experimentos: {stats['experiments_count']}")
    print(f"  Runs:         {stats['runs_count']}")
    
    # 2. Verificar método has_data()
    has_data = db.has_data()
    print(f"\n✅ db.has_data() = {has_data}")
    
    # 3. Intentar obtener todos los runs
    print("\n🔄 Intentando obtener runs...")
    try:
        all_runs = db.get_all_runs()
        print(f"✅ get_all_runs() retornó {len(all_runs)} filas")
        
        if not all_runs.empty:
            print(f"\n📋 Columnas disponibles:")
            for col in all_runs.columns:
                print(f"  - {col}")
            
            print(f"\n📊 Primeras 5 filas:")
            print(all_runs[['solver', 'benchmark', 'result', 'wall_time_seconds']].head())
            
            print(f"\n⚙️  Solvers únicos:")
            for solver in all_runs['solver'].unique():
                count = len(all_runs[all_runs['solver'] == solver])
                print(f"  - {solver}: {count} runs")
        else:
            print("❌ get_all_runs() retornó DataFrame vacío")
            
    except Exception as e:
        print(f"❌ Error obteniendo runs: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Verificar tabla runs directamente
    print("\n🔍 Verificando tabla runs directamente...")
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM runs")
    run_count = cursor.fetchone()['count']
    print(f"  Runs en tabla: {run_count}")
    
    if run_count > 0:
        # Verificar si tienen relaciones correctas
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT solver_id) as unique_solvers,
                COUNT(DISTINCT benchmark_id) as unique_benchmarks,
                COUNT(DISTINCT experiment_id) as unique_experiments
            FROM runs
        """)
        
        relations = cursor.fetchone()
        print(f"\n🔗 RELACIONES:")
        print(f"  Total runs:          {relations['total']}")
        print(f"  Solvers únicos:      {relations['unique_solvers']}")
        print(f"  Benchmarks únicos:   {relations['unique_benchmarks']}")
        print(f"  Experimentos únicos: {relations['unique_experiments']}")
        
        # Verificar si hay runs sin solver_id válido
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM runs r
            LEFT JOIN solvers s ON r.solver_id = s.id
            WHERE s.id IS NULL
        """)
        orphan_solver = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM runs r
            LEFT JOIN benchmarks b ON r.benchmark_id = b.id
            WHERE b.id IS NULL
        """)
        orphan_benchmark = cursor.fetchone()['count']
        
        print(f"\n⚠️  PROBLEMAS:")
        print(f"  Runs sin solver válido:    {orphan_solver}")
        print(f"  Runs sin benchmark válido: {orphan_benchmark}")
        
        if orphan_solver > 0 or orphan_benchmark > 0:
            print("\n❌ HAY RUNS CON REFERENCIAS INVÁLIDAS")
            print("   Esto causa que get_all_runs() no retorne esos datos")
    
    conn.close()
    
    # 5. Listar experimentos
    print("\n🧪 EXPERIMENTOS:")
    experiments = db.get_experiments()
    if experiments:
        for exp in experiments:
            print(f"  - ID {exp['id']}: {exp['name']} ({exp['status']})")
            print(f"    Runs: {exp['completed_runs']}/{exp['total_runs']}")
    else:
        print("  No hay experimentos")

if __name__ == "__main__":
    check_database()