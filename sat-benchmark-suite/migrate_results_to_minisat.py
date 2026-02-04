"""
Script para normalizar nombres de benchmarks y migrar resultados
Corrige errores tipográficos comunes en nombres de archivos
"""

import sys
from pathlib import Path
import csv
from datetime import datetime
import re
from difflib import SequenceMatcher

sys.path.append(str(Path(__file__).parent))

from app.core.database import DatabaseManager


def normalize_filename(filename: str) -> str:
    """Normaliza nombres de archivos eliminando errores comunes"""
    
    # Eliminar dobles caracteres comunes
    normalized = filename
    
    # Corregir dobles letras comunes
    replacements = {
        'liist': 'list',
        'saanitized': 'sanitized',
        'ssanitized': 'sanitized',
        'sshuffled': 'shuffled',
        'shufflingg': 'shuffling',
        'miiters': 'miters',
        'unssats': 'unsat',
        'syntheesis': 'synthesis',
        'schheduling': 'scheduling',
        'Randomm': 'Random',
        'unssat': 'unsat',
        'rr17': 'r17',
        'rr16': 'r16',
        'r166': 'r16',
        'r188': 'r18',
        'r199': 'r19',
        'r200': 'r20',
        'r211': 'r21',
        'r244': 'r24',
        'pp20': 'p20',
        'collour': 'colour',
        'triiple': 'triple',
        'hwmcc115': 'hwmcc15',
        'hwmcc20': 'hwmcc20',
        'kliebber': 'klieber',
        'bboothb': 'boothb',
        'ak128b': 'ak128',
    }
    
    for wrong, correct in replacements.items():
        normalized = normalized.replace(wrong, correct)
    
    # Eliminar espacios al final
    normalized = normalized.strip()
    
    # Corregir dobles guiones bajos
    normalized = re.sub(r'__+', '_', normalized)
    
    # Corregir dobles puntos
    normalized = re.sub(r'\.\.+', '.', normalized)
    
    # Corregir dobles hashes
    normalized = re.sub(r'##', '#', normalized)
    
    return normalized


def find_best_match(target: str, candidates: list, threshold=0.85) -> str:
    """Encuentra el mejor match usando similitud de strings"""
    
    best_match = None
    best_ratio = 0
    
    target_normalized = normalize_filename(target)
    
    for candidate in candidates:
        # Calcular similitud
        ratio = SequenceMatcher(None, target_normalized.lower(), candidate.lower()).ratio()
        
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = candidate
    
    return best_match


def migrate_with_name_fixing(csv_path: str, solver_name: str = "minisat"):
    """Migra datos arreglando nombres de archivos"""
    
    print("=" * 60)
    print("🔧 MIGRACIÓN CON CORRECCIÓN DE NOMBRES")
    print("=" * 60)
    
    db = DatabaseManager()
    
    # Verificar solver
    solver_id = db.get_solver_id_by_name(solver_name)
    if not solver_id:
        print(f"❌ Solver '{solver_name}' no encontrado")
        return
    
    print(f"✅ Solver: {solver_name} (ID: {solver_id})")
    
    # Obtener todos los benchmarks de la BD
    print("\n📂 Cargando benchmarks de la BD...")
    all_benchmarks = db.get_benchmarks()
    benchmark_names = [b['filename'] for b in all_benchmarks]
    benchmark_map = {b['filename']: b['id'] for b in all_benchmarks}
    
    print(f"✅ Cargados {len(benchmark_names)} benchmarks de la BD")
    
    # Cargar CSV
    print(f"\n📂 Leyendo CSV: {csv_path}")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"✅ Cargadas {len(rows)} filas del CSV")
    
    # Mostrar columnas disponibles
    if rows:
        print(f"\n📋 Columnas en CSV: {list(rows[0].keys())[:10]}...")
    
    # Verificar si experimento existe
    experiment_name = "MiniSat Complete Results"
    exp_id = db.get_experiment_id_by_name(experiment_name)
    
    if exp_id:
        print(f"\n⚠️  Experimento '{experiment_name}' ya existe (ID: {exp_id})")
        response = input("   ¿Usar experimento existente y agregar runs? (yes/no): ")
        
        if response.lower() != 'yes':
            from datetime import datetime as dt
            timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
            experiment_name = f"MiniSat Complete Results {timestamp}"
            print(f"   Creando nuevo experimento: {experiment_name}")
            
            exp_id = db.create_experiment(
                name=experiment_name,
                description=f"Datos migrados desde {csv_path} con corrección de nombres",
                timeout_seconds=5000,
                metadata={
                    'migrated_from': csv_path,
                    'name_fixing': True
                }
            )
        else:
            print(f"   Usando experimento existente ID {exp_id}")
    else:
        exp_id = db.create_experiment(
            name=experiment_name,
            description=f"Datos migrados desde {csv_path} con corrección de nombres",
            timeout_seconds=5000,
            metadata={
                'migrated_from': csv_path,
                'name_fixing': True
            }
        )
    
    print(f"✅ Experimento: ID {exp_id}")
    
    # Procesar resultados
    print("\n🔄 Procesando y corrigiendo nombres...")
    
    stats = {
        'total': len(rows),
        'migrated': 0,
        'fixed_names': 0,
        'skipped': 0,
        'errors': []
    }
    
    for i, row in enumerate(rows, 1):
        try:
            original_name = row.get('benchmark', '')
            
            if not original_name:
                stats['skipped'] += 1
                continue
            
            # Agregar .cnf si falta
            if not original_name.endswith('.cnf'):
                original_name = original_name + '.cnf'
            
            # Intentar buscar directo
            benchmark_id = benchmark_map.get(original_name)
            fixed_name = original_name
            
            # Si no se encuentra, intentar normalizar
            if not benchmark_id:
                normalized_name = normalize_filename(original_name)
                benchmark_id = benchmark_map.get(normalized_name)
                
                if benchmark_id:
                    fixed_name = normalized_name
                    stats['fixed_names'] += 1
                else:
                    # Buscar match aproximado
                    best_match = find_best_match(original_name, benchmark_names, threshold=0.90)
                    
                    if best_match:
                        benchmark_id = benchmark_map[best_match]
                        fixed_name = best_match
                        stats['fixed_names'] += 1
                        
                        if stats['fixed_names'] <= 10:
                            print(f"  ✓ '{original_name}' → '{best_match}'")
            
            if not benchmark_id:
                stats['skipped'] += 1
                if stats['skipped'] <= 5:
                    print(f"  ⚠️ No encontrado: {original_name}")
                continue
            
            # ========== FIX: Extraer datos del CSV correctamente ==========
            
            result = str(row.get('result', 'UNKNOWN')).upper()
            exit_code = int(row.get('exit_code', 0)) if row.get('exit_code') else 0
            
            # Tiempos - Usar las columnas exactas del CSV
            def safe_float(value, default=0.0):
                if not value or value == '' or value == 'None':
                    return default
                try:
                    return float(value)
                except:
                    return default
            
            cpu_time = safe_float(row.get('cpu_time_seconds', '0'))
            system_time = safe_float(row.get('system_time_seconds', '0'))
            wall_time = safe_float(row.get('wall_time_seconds', '0'))
            
            # Si wall_time es 0 pero hay cpu_time, usar cpu_time
            if wall_time == 0.0 and cpu_time > 0:
                wall_time = cpu_time
            
            # Memoria
            max_memory = int(safe_float(row.get('max_memory_kb', '0')))
            avg_memory = int(safe_float(row.get('avg_memory_kb', str(max_memory))))
            
            # CPU percentage
            cpu_percentage = safe_float(row.get('cpu_percentage', '0'))
            
            # System stats
            page_faults_major = int(safe_float(row.get('major_page_faults', '0')))
            page_faults_minor = int(safe_float(row.get('minor_page_faults', '0')))
            page_faults = page_faults_major + page_faults_minor
            
            ctx_switch_vol = int(safe_float(row.get('voluntary_context_switches', '0')))
            ctx_switch_invol = int(safe_float(row.get('involuntary_context_switches', '0')))
            
            # Métricas del solver
            def safe_int(value):
                if not value or value == '' or value == 'None':
                    return None
                try:
                    return int(float(value))
                except:
                    return None
            
            conflicts = safe_int(row.get('conflicts', ''))
            decisions = safe_int(row.get('decisions', ''))
            propagations = safe_int(row.get('propagations', ''))
            restarts = safe_int(row.get('restarts', ''))
            learnt_literals = safe_int(row.get('learnt_literals', ''))
            deleted_literals = safe_int(row.get('deleted_literals', ''))
            learnt_clauses = safe_int(row.get('learned_clauses_deleted', ''))
            
            # PAR-2 Score
            timeout = 5000
            if result in ['TIMEOUT', 'MEMOUT', 'ERROR']:
                par2_score = 2 * timeout
            else:
                par2_score = wall_time if wall_time > 0 else cpu_time
            
            # Preparar kwargs con TODOS los campos necesarios
            run_data = {
                'experiment_id': exp_id,
                'solver_id': solver_id,
                'benchmark_id': benchmark_id,
                
                # Resultado
                'result': result,
                'exit_code': exit_code,
                'verified': False,
                
                # Tiempos
                'cpu_time_seconds': cpu_time,
                'wall_time_seconds': wall_time,
                'user_time_seconds': cpu_time,  # Aproximación
                'system_time_seconds': system_time,
                
                # Memoria
                'max_memory_kb': max_memory,
                'avg_memory_kb': avg_memory,
                
                # System stats
                'page_faults': page_faults,
                'context_switches_voluntary': ctx_switch_vol,
                'context_switches_involuntary': ctx_switch_invol,
                'cpu_percentage': cpu_percentage,
                
                # Solver statistics
                'conflicts': conflicts,
                'decisions': decisions,
                'propagations': propagations,
                'restarts': restarts,
                'learnt_literals': learnt_literals,
                'deleted_literals': deleted_literals,
                'learnt_clauses': learnt_clauses,
                'deleted_clauses': None,
                
                # Additional metrics
                'max_learnt_clauses': None,
                'avg_learnt_clause_length': safe_float(row.get('avg_clause_length', '')),
                'decision_height_avg': None,
                'decision_height_max': None,
                
                # Metadata
                'timestamp': datetime.now(),
                'hostname': None,
                'solver_output': '',
                'error_message': '',
                
                # Performance
                'par2_score': par2_score
            }
            
            # Agregar run usando **kwargs
            db.add_run(**run_data)
            
            stats['migrated'] += 1
            
            if i % 50 == 0:
                print(f"  Progreso: {i}/{stats['total']} ({stats['migrated']} migrados, {stats['fixed_names']} nombres corregidos)")
        
        except Exception as e:
            stats['errors'].append({
                'row': i,
                'benchmark': original_name if 'original_name' in locals() else 'Unknown',
                'error': str(e)
            })
            
            # Debug: mostrar primeros 3 errores completos
            if len(stats['errors']) <= 3:
                import traceback
                print(f"\n❌ Error en fila {i}:")
                traceback.print_exc()
    
    # Actualizar experimento
    db.update_experiment_status(
        exp_id,
        'completed',
        total_runs=stats['migrated'],
        completed_runs=stats['migrated'],
        completed_at=datetime.now()
    )
    
    # Resumen
    print(f"\n{'=' * 60}")
    print("✅ MIGRACIÓN COMPLETADA")
    print(f"{'=' * 60}")
    print(f"  Total filas CSV:         {stats['total']}")
    print(f"  ✅ Migrados exitosos:    {stats['migrated']}")
    print(f"  🔧 Nombres corregidos:   {stats['fixed_names']}")
    print(f"  ⏭️  Omitidos:             {stats['skipped']}")
    print(f"  ❌ Errores:              {len(stats['errors'])}")
    
    if stats['errors']:
        print(f"\n⚠️ Errores (primeros 10):")
        for error in stats['errors'][:10]:
            print(f"  - Fila {error['row']}: {error.get('benchmark', 'Unknown')} - {error['error']}")
    
    print(f"\n🎯 Experimento ID: {exp_id}")
    print(f"   Solver: {solver_name} (ID: {solver_id})")
    print(f"\n✅ Verifica en la app:")
    print("   streamlit run app/main.py")
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrar con corrección de nombres")
    parser.add_argument('--csv', default='../resultados/results_complete.csv', help='Ruta al CSV')
    parser.add_argument('--solver', default='minisat', help='Nombre del solver')
    
    args = parser.parse_args()
    
    # Buscar CSV
    csv_path = args.csv
    if not Path(csv_path).exists():
        csv_candidates = [
            "../resultados/results_complete.csv",
            "results/results_complete.csv",
            "results_complete.csv"
        ]
        
        for candidate in csv_candidates:
            if Path(candidate).exists():
                csv_path = candidate
                break
    
    if not Path(csv_path).exists():
        print(f"❌ CSV no encontrado: {csv_path}")
        exit(1)
    
    migrate_with_name_fixing(csv_path, args.solver)