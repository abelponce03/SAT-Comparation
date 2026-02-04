"""
Script de diagnóstico completo para Kissat
"""

import sys
from pathlib import Path
import subprocess
import os

sys.path.append(str(Path(__file__).parent))

from app.core.database import DatabaseManager

def diagnose_kissat():
    print("=" * 60)
    print("🔍 DIAGNÓSTICO COMPLETO: KISSAT")
    print("=" * 60)
    
    # 1. Verificar estructura de carpetas
    print("\n1️⃣  Verificando estructura de carpetas...")
    
    kissat_dir = Path("solvers/kissat")
    
    if not kissat_dir.exists():
        print(f"❌ Carpeta no existe: {kissat_dir}")
        return
    
    print(f"✅ Carpeta existe: {kissat_dir.absolute()}")
    
    # 2. Verificar código fuente
    print("\n2️⃣  Verificando código fuente...")
    
    essential_files = [
        "configure",
        "makefile.in",
        "src/main.c",
        "src/kissat.h"
    ]
    
    missing_files = []
    for file in essential_files:
        file_path = kissat_dir / file
        if file_path.exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file}")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️  Faltan {len(missing_files)} archivos esenciales")
        return
    
    # 3. Verificar compilación
    print("\n3️⃣  Verificando compilación...")
    
    build_dir = kissat_dir / "build"
    executable = build_dir / "kissat"
    
    if not build_dir.exists():
        print(f"❌ Carpeta build NO existe: {build_dir}")
        print("\n⚠️  Kissat NO está compilado")
        print("\n🔨 Para compilar:")
        print("   cd solvers/kissat")
        print("   ./configure")
        print("   make")
    elif not executable.exists():
        print(f"❌ Ejecutable NO existe: {executable}")
        print("\n⚠️  Compilación incompleta")
        print("\n🔨 Para recompilar:")
        print("   cd solvers/kissat")
        print("   make clean")
        print("   ./configure")
        print("   make")
    else:
        print(f"✅ Ejecutable existe: {executable.absolute()}")
        
        # Verificar permisos
        if os.name != 'nt' and not os.access(executable, os.X_OK):
            print(f"⚠️  Sin permisos de ejecución")
            print("   Agregando permisos...")
            executable.chmod(0o755)
            print("   ✅ Permisos agregados")
        
        # 4. Probar ejecución
        print("\n4️⃣  Probando ejecución del solver...")
        
        try:
            result = subprocess.run(
                [str(executable), "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                print(f"✅ Ejecutable funciona correctamente")
                print(f"\n📋 Output:")
                for line in result.stdout.strip().split('\n')[:5]:
                    print(f"   {line}")
            else:
                print(f"❌ Error al ejecutar (exit code: {result.returncode})")
                print(f"\n📋 Stderr:")
                print(result.stderr)
        
        except FileNotFoundError:
            print(f"❌ No se puede ejecutar el archivo")
        except subprocess.TimeoutExpired:
            print(f"⚠️  Timeout al ejecutar")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # 5. Verificar configuración en BD
    print("\n5️⃣  Verificando configuración en base de datos...")
    
    db = DatabaseManager()
    solvers = db.get_solvers()
    
    kissat_solver = None
    for solver in solvers:
        if solver['name'].lower() == 'kissat':
            kissat_solver = solver
            break
    
    if not kissat_solver:
        print("❌ Solver 'kissat' NO está registrado en la BD")
        print("\n📝 Para agregar:")
        print("   1. Ve a la app: streamlit run app/main.py")
        print("   2. Setup Solvers → Add Solver")
        print(f"   3. Ejecutable: {executable.absolute() if executable.exists() else 'Compila primero'}")
    else:
        print(f"✅ Solver registrado: {kissat_solver['name']} (ID: {kissat_solver['id']})")
        print(f"   Estado:     {kissat_solver['status']}")
        print(f"   Ejecutable: {kissat_solver['executable_path']}")
        
        # Verificar si path es correcto
        configured_path = Path(kissat_solver['executable_path'])
        
        if not configured_path.exists():
            print(f"\n❌ Path configurado NO existe")
        elif configured_path.suffix in ['.h', '.hpp', '.c', '.cpp']:
            print(f"\n❌ Path apunta a código fuente (.{configured_path.suffix})")
            print("   Debe apuntar al ejecutable compilado")
        elif configured_path != executable:
            print(f"\n⚠️  Path configurado es diferente al ejecutable real")
            print(f"   Configurado: {configured_path}")
            print(f"   Real:        {executable}")
        else:
            print(f"\n✅ Path configurado es correcto")
    
    # 6. Verificar benchmarks
    print("\n6️⃣  Verificando benchmarks...")
    
    benchmarks_dir = Path("benchmarks")
    
    if not benchmarks_dir.exists():
        print(f"❌ Carpeta de benchmarks no existe: {benchmarks_dir}")
    else:
        cnf_files = list(benchmarks_dir.glob("*.cnf"))
        print(f"✅ Benchmarks disponibles: {len(cnf_files)}")
        
        if len(cnf_files) > 0:
            # Probar con un benchmark
            test_benchmark = cnf_files[0]
            print(f"\n🧪 Probando con: {test_benchmark.name}")
            
            if executable.exists():
                try:
                    result = subprocess.run(
                        [str(executable), str(test_benchmark)],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode in [10, 20, 0]:
                        print(f"✅ Ejecución exitosa (exit code: {result.returncode})")
                        
                        # Mostrar primeras líneas de output
                        lines = result.stdout.strip().split('\n')
                        print(f"\n📋 Output (primeras 10 líneas):")
                        for line in lines[:10]:
                            print(f"   {line}")
                    else:
                        print(f"⚠️  Exit code inesperado: {result.returncode}")
                        print(f"\n📋 Stderr:")
                        print(result.stderr[:500])
                
                except subprocess.TimeoutExpired:
                    print(f"✅ Solver ejecutándose (timeout a 10s - normal para benchmarks grandes)")
                except Exception as e:
                    print(f"❌ Error: {e}")
    
    # 7. Resumen y recomendaciones
    print("\n" + "=" * 60)
    print("📋 RESUMEN Y RECOMENDACIONES")
    print("=" * 60)
    
    recommendations = []
    
    if not executable.exists():
        recommendations.append("🔨 Compilar Kissat:")
        recommendations.append("   cd solvers/kissat")
        recommendations.append("   ./configure")
        recommendations.append("   make")
    
    if kissat_solver is None:
        recommendations.append("\n📝 Registrar solver en BD:")
        recommendations.append("   python update_kissat_path.py")
    elif not Path(kissat_solver['executable_path']).exists():
        recommendations.append("\n🔄 Actualizar path en BD:")
        recommendations.append("   python update_kissat_path.py")
    
    if recommendations:
        print("\n⚠️  Acciones requeridas:")
        for rec in recommendations:
            print(rec)
    else:
        print("\n✅ ¡Todo está configurado correctamente!")
        print("\n🚀 Puedes crear y ejecutar experimentos con Kissat")


if __name__ == "__main__":
    diagnose_kissat()