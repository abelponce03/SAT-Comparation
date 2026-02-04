"""
Script para limpiar experimentos anteriores y ejecutar migración limpia
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from app.core.database import DatabaseManager
from migrate_results_to_minisat import migrate_with_name_fixing

def clean_and_migrate():
    db = DatabaseManager()
    
    print("=" * 60)
    print("🧹 LIMPIEZA Y MIGRACIÓN")
    print("=" * 60)
    
    # 1. Listar experimentos existentes
    experiments = db.get_experiments()
    
    if experiments:
        print("\n📋 Experimentos existentes:")
        for exp in experiments:
            print(f"  - ID {exp['id']}: {exp['name']} ({exp['status']})")
            print(f"    Runs: {exp['completed_runs']}/{exp['total_runs']}")
        
        # 2. Preguntar si eliminar
        response = input("\n¿Eliminar TODOS los experimentos anteriores? (yes/no): ")
        
        if response.lower() == 'yes':
            for exp in experiments:
                db.delete_experiment(exp['id'])
                print(f"  ✅ Eliminado experimento ID {exp['id']}")
            
            print("\n✅ Limpieza completada")
        else:
            print("\n⏭️  Manteniendo experimentos existentes")
    else:
        print("\n✅ No hay experimentos para limpiar")
    
    # 3. Ejecutar migración
    print("\n" + "=" * 60)
    print("🚀 INICIANDO MIGRACIÓN")
    print("=" * 60 + "\n")
    
    csv_path = "../resultados/results_complete.csv"
    
    if not Path(csv_path).exists():
        print(f"❌ CSV no encontrado: {csv_path}")
        return
    
    migrate_with_name_fixing(csv_path, solver_name="minisat")

if __name__ == "__main__":
    clean_and_migrate()