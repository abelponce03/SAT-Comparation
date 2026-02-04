# SAT Benchmark React

Framework moderno para análisis comparativo de solvers SAT, desarrollado como parte de trabajo de tesis.

## 🎯 Objetivos

- **Analizar comparativamente** la eficiencia temporal de distintos solucionadores SAT
- **Framework reproducible** para benchmarking y evaluación
- **Análisis estadístico riguroso** (PAR-2, VBS, ECDF, Performance Profiles)
- **Visualización interactiva** de resultados (Cactus plots, Scatter plots, Heatmaps)

## 🏗️ Arquitectura

```
sat-benchmark-react/
├── backend/                 # FastAPI + SQLite
│   ├── app/
│   │   ├── main.py         # Entry point
│   │   ├── core/           # Database, config
│   │   └── api/            # REST endpoints
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/               # React + TypeScript
│   ├── src/
│   │   ├── pages/          # Dashboard, Solvers, Benchmarks, etc.
│   │   ├── components/     # Reusable UI components
│   │   ├── services/       # API client
│   │   └── types/          # TypeScript definitions
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml      # Orquestación
└── nginx/                  # Reverse proxy (producción)
```

## 🚀 Quick Start

### Prerrequisitos

- Docker y Docker Compose
- O alternativamente: Python 3.11+, Node.js 20+

### Con Docker (Recomendado)

```bash
# Clonar e iniciar
cd sat-benchmark-react
docker-compose up -d

# Acceder a la aplicación
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Desarrollo Local

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## 📊 Características

### Gestión de Solvers
- Registro de solvers SAT (Kissat, MiniSat, CaDiCaL, etc.)
- Templates predefinidos para solvers populares
- Compilación automática
- Testing de funcionalidad

### Gestión de Benchmarks
- Importación de archivos CNF (individual o por lotes)
- Clasificación automática por familia
- Vista previa del contenido
- Metadatos: variables, cláusulas, ratio

### Experimentos
- Configuración: timeout, límite de memoria, jobs paralelos
- Selección flexible de solvers y benchmarks
- Ejecución con monitoreo en tiempo real
- Exportación de resultados CSV

### Análisis Estadístico
- **PAR-2 Score**: Penalized Average Runtime
- **VBS (Virtual Best Solver)**: Rendimiento teórico óptimo
- **Comparación por pares**: Head-to-head entre solvers
- **Análisis por familia**: Desglose por tipo de instancia

### Visualización
- **Cactus Plot**: Instancias resueltas vs tiempo
- **Scatter Plot**: Comparación directa entre dos solvers
- **ECDF/Performance Profile**: Distribución de performance ratios
- **Heatmap**: Vista matricial de tiempos

## 🔧 Stack Tecnológico

### Backend
- **FastAPI**: Framework web async
- **SQLite**: Base de datos embebida
- **Pandas/NumPy**: Análisis estadístico
- **Pydantic**: Validación de datos

### Frontend
- **React 18**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool
- **TailwindCSS**: Styling
- **TanStack Query**: Data fetching
- **Recharts**: Visualización
- **React Router v6**: Navegación

## 📁 API Endpoints

| Endpoint | Descripción |
|----------|-------------|
| `GET /api/dashboard/stats` | Estadísticas generales |
| `GET /api/solvers` | Listar solvers |
| `POST /api/solvers` | Registrar solver |
| `POST /api/solvers/{id}/compile` | Compilar solver |
| `GET /api/benchmarks` | Listar benchmarks |
| `POST /api/benchmarks/upload` | Subir archivos CNF |
| `GET /api/experiments` | Listar experimentos |
| `POST /api/experiments` | Crear experimento |
| `POST /api/experiments/{id}/start` | Iniciar ejecución |
| `GET /api/analysis/par2` | Análisis PAR-2 |
| `GET /api/analysis/vbs` | Análisis VBS |
| `GET /api/analysis/cactus` | Datos cactus plot |

Ver documentación completa en: `http://localhost:8000/docs`

## 📈 Métricas Implementadas

### PAR-2 (Penalized Average Runtime)
$$PAR_k = \frac{1}{n} \sum_{i=1}^{n} t_i^{PAR_k}$$

Donde:
$$t_i^{PAR_k} = \begin{cases} t_i & \text{si resuelto} \\ k \cdot T_{max} & \text{si timeout} \end{cases}$$

### Virtual Best Solver (VBS)
$$t_{VBS}(p) = \min_{s \in S} t_s(p)$$

### Performance Profile
$$\rho_s(\tau) = \frac{|\{p \in P : r_{p,s} \leq \tau\}|}{|P|}$$

## 🎓 Para la Tesis

Este framework está diseñado para:

1. **Reproducibilidad**: Configuración Docker, seeds fijos, logs completos
2. **Rigor estadístico**: Métricas estándar de la comunidad SAT
3. **Extensibilidad**: Fácil agregar nuevos solvers y métricas
4. **Documentación**: Código comentado, API documentada

## 📝 Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles.

## 🤝 Contribuciones

Este es un proyecto de tesis. Para sugerencias, abrir un issue.
