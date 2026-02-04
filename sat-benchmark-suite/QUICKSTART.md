# 🚀 Quick Start Guide - SAT Benchmark Suite

## ⚡ Inicio Rápido (5 minutos)

### Paso 1: Instalar Dependencias
```bash
cd sat-benchmark-suite
pip install -r requirements.txt
```

### Paso 2: Iniciar la Aplicación
```bash
python start.py
```

**O manualmente:**
```bash
streamlit run app/main.py
```

### Paso 3: Abrir en el Navegador
Abre automáticamente o navega a: **http://localhost:8501**

---

## 📊 Migrar Datos Existentes (Opcional)

Si ya tienes resultados en `results_complete.csv`:

```bash
python migrate_existing_data.py
```

Esto importará:
- ✅ Solver MiniSat
- ✅ 400 benchmarks (con metadata)
- ✅ 400 runs con todas las métricas

---

## 🎯 Primeros Pasos en la Aplicación

### 1. Página Principal
- Verás el **overview** del sistema
- Estadísticas en el sidebar
- Features disponibles

### 2. ⚙️ Setup Solvers
**Agregar tu primer solver:**

#### Opción A: Solver Pre-compilado
1. Ve a "Add Solver" → "Quick Add"
2. Nombre: `minisat`
3. Ejecutable: ruta a tu `minisat.exe` o `minisat`
4. Click "Add Pre-compiled Solver"

#### Opción B: Upload y Compilar
1. Ve a "Add Solver" → "Upload Archive"
2. Sube ZIP/TAR.GZ del código fuente
3. Nombre del solver
4. Sistema auto-detecta build
5. Ve a "Compile Solver"
6. Click "Compile Now"
7. Espera logs de compilación

### 3. 📁 Manage Benchmarks (Por implementar)
Próximamente podrás:
- Escanear directorio de CNFs
- Upload múltiples benchmarks
- Ver clasificación automática

### 4. 🚀 Run Experiments (Por implementar)
Próximamente podrás:
- Crear experimentos
- Seleccionar solvers × benchmarks
- Lanzar y monitorear en tiempo real

---

## 🔧 Verificar Instalación

### Check 1: Python
```bash
python --version
```
Debe ser **Python 3.8+**

### Check 2: Streamlit
```bash
streamlit --version
```
Debe mostrar versión instalada

### Check 3: Base de Datos
Después de iniciar, verifica que existe:
```
sat-benchmark-suite/results/experiments.db
```

---

## 📂 Estructura de Archivos Importantes

```
sat-benchmark-suite/
├── app/main.py                    ← Página principal
├── app/pages/
│   └── 1_⚙️_Setup_Solvers.py    ← Gestión de solvers (FUNCIONAL)
├── config/
│   ├── app_config.yaml            ← Configuración general
│   └── solver_templates.json      ← Templates de solvers
├── solvers/                       ← AQUÍ van tus solvers
├── benchmarks/                    ← AQUÍ van tus CNFs
└── results/
    └── experiments.db             ← Base de datos (auto-creada)
```

---

## 🐛 Solución de Problemas Comunes

### Error: "ModuleNotFoundError: No module named 'streamlit'"
**Solución:**
```bash
pip install -r requirements.txt
```

### Error: "Database is locked"
**Solución:**
- Cierra otras instancias de la aplicación
- O borra `results/experiments.db` (perderás datos)

### Error: Solver no compila
**Solución:**
1. Verifica que tienes `gcc`, `make`, `cmake` instalados
2. Lee los logs de compilación en la interfaz
3. Intenta compilar manualmente primero
4. Luego agrega como pre-compilado

### La aplicación no abre en el navegador
**Solución:**
- Abre manualmente: http://localhost:8501
- O usa: `streamlit run app/main.py --server.headless false`

---

## 💡 Consejos

1. **Empieza probando con un solver** (MiniSat es fácil)
2. **Prueba con pocos benchmarks** primero (5-10)
3. **Revisa el README.md** para documentación completa
4. **Consulta ROADMAP.md** para ver qué viene próximamente
5. **Los logs** aparecen en la terminal donde ejecutaste

---

## 📧 Siguiente Paso

Después de iniciar la aplicación, dime:

**¿Qué quieres implementar primero?**
- **A)** Gestión de Benchmarks (ver/filtrar tus CNFs)
- **B)** Ejecución de Experimentos (correr solvers)
- **C)** Visualización de Resultados (ver datos migrados)
- **D)** Análisis Estadístico (PAR-2, comparaciones)

---

## ✅ Checklist de Inicio

- [ ] Python 3.8+ instalado
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Aplicación iniciada (`python start.py`)
- [ ] Navegador abierto en http://localhost:8501
- [ ] (Opcional) Datos migrados (`python migrate_existing_data.py`)
- [ ] Al menos 1 solver agregado
- [ ] Benchmarks copiados a carpeta `benchmarks/`

**¡Listo para comenzar! 🎉**
