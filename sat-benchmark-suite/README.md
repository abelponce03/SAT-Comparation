# 🔬 SAT Benchmark Suite

A comprehensive benchmarking and analysis platform for SAT solvers. Built with Python and Streamlit.

## ✨ Features

- **⚙️ Solver Management**: Upload, auto-compile, and manage multiple SAT solvers
- **📁 Benchmark Management**: Auto-classify benchmarks by problem family with metadata extraction
- **🚀 Experiment Execution**: Parallel execution with real-time monitoring
- **📊 Results Management**: SQLite database for efficient result storage and querying
- **📈 Statistical Analysis**: PAR-2, VBS, confidence intervals, and more
- **📉 Visualization**: Cactus plots, scatter plots, and heatmaps
- **📄 Report Generation**: Automated PDF/HTML report generation

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd sat-benchmark-suite
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   streamlit run app/main.py
   ```

4. **Open your browser** to `http://localhost:8501`

## 📁 Project Structure

```
sat-benchmark-suite/
├── app/
│   ├── main.py                          # Main application page
│   ├── pages/
│   │   ├── 1_⚙️_Setup_Solvers.py       # Solver management
│   │   ├── 2_📁_Manage_Benchmarks.py   # Benchmark management
│   │   ├── 3_🚀_Run_Experiments.py     # Experiment execution
│   │   ├── 4_📊_View_Results.py        # Results viewer
│   │   ├── 5_📈_Statistical_Analysis.py # Statistical tools
│   │   ├── 6_📉_Visualizations.py      # Plotting tools
│   │   └── 7_📄_Reports.py             # Report generator
│   ├── core/
│   │   ├── database.py                  # SQLite manager
│   │   ├── solver_manager.py            # Solver operations
│   │   ├── benchmark_manager.py         # Benchmark operations
│   │   ├── executor.py                  # Experiment executor
│   │   └── monitor.py                   # Real-time monitoring
│   ├── analysis/
│   │   ├── statistics.py                # Statistical analysis
│   │   └── plots.py                     # Plotting functions
│   └── utils/
│       ├── cnf_parser.py                # CNF file parser
│       ├── solver_detector.py           # Auto-detect solvers
│       └── helpers.py                   # Helper functions
├── solvers/                             # Your solvers go here
├── benchmarks/                          # Your CNF files go here
├── results/
│   ├── experiments.db                   # SQLite database
│   └── exports/                         # Exported CSVs
├── config/
│   ├── app_config.yaml                  # App configuration
│   └── solver_templates.json            # Solver templates
└── requirements.txt                     # Python dependencies
```

## 📖 Usage Guide

### 1. Setup Solvers

Navigate to **⚙️ Setup Solvers** page:

- **Upload Archive**: Upload ZIP/TAR.GZ of solver source code
- **Auto-compilation**: System auto-detects Makefile and compiles
- **Manual configuration**: Specify custom build commands
- **Pre-compiled**: Add already compiled solvers

**Supported Solvers:**
- MiniSat
- CaDiCaL
- Glucose
- CryptoMiniSat
- Kissat
- Lingeling
- Any custom solver

### 2. Add Benchmarks

Navigate to **📁 Manage Benchmarks** page:

- **Scan Directory**: Auto-discover CNF files
- **Upload**: Upload individual or multiple benchmarks
- **Auto-classification**: System classifies by problem family
- **Metadata Extraction**: Automatically extracts variables, clauses, ratio

### 3. Run Experiments

Navigate to **🚀 Run Experiments** page:

1. **Create Experiment**: Give it a name and description
2. **Select Solvers**: Choose which solvers to benchmark
3. **Select Benchmarks**: Filter and select benchmarks
4. **Configure**: Set timeout, memory limit, parallel jobs
5. **Launch**: Monitor progress in real-time

### 4. View Results

Navigate to **📊 View Results** page:

- **Filter**: By solver, benchmark family, result status
- **Export**: Download as CSV or Excel
- **Details**: View complete run information
- **Compare**: Side-by-side comparison

### 5. Statistical Analysis

Navigate to **📈 Statistical Analysis** page:

- **PAR-2 Scoring**: Penalized average runtime
- **Virtual Best Solver (VBS)**: Best possible performance
- **Pairwise Comparisons**: Statistical significance tests
- **Confidence Intervals**: Bootstrap or t-distribution

### 6. Visualizations

Navigate to **📉 Visualizations** page:

- **Cactus Plot**: Solved instances over time
- **Scatter Plot**: Solver A vs Solver B runtime
- **Heatmap**: Result matrix
- **Performance Profile**: Cumulative distribution

### 7. Generate Reports

Navigate to **📄 Reports** page:

- **PDF Reports**: Publication-ready documents
- **HTML Reports**: Interactive web pages
- **Custom Templates**: Customize report structure
- **Include Plots**: Embed all visualizations

## ⚙️ Configuration

### Database Configuration

The SQLite database stores:
- **Solvers**: Name, version, executable path, compilation info
- **Benchmarks**: Metadata, classification, checksums
- **Experiments**: Configuration, status, timing
- **Runs**: Complete results with 40+ metrics per run

### Solver Templates

Edit `config/solver_templates.json` to add templates for new solvers:

```json
{
  "your_solver": {
    "name": "Your Solver",
    "build_files": ["Makefile"],
    "build_commands": ["make"],
    "executable_patterns": ["build/your_solver"],
    "test_command": "{executable} --version"
  }
}
```

### Application Settings

Edit `config/app_config.yaml`:

```yaml
defaults:
  timeout_seconds: 5000
  memory_limit_mb: 8192
  parallel_jobs: 4

benchmark_families:
  - name: "custom"
    pattern: "custom_.*"
    description: "Custom Problems"
```

## 📊 Metrics Collected

For each run, the system collects:

### Basic Metrics
- Result (SAT/UNSAT/TIMEOUT/MEMOUT/ERROR)
- CPU time, wall time, system time
- Memory usage (max, average)
- Exit code

### System Metrics
- Page faults
- Context switches
- CPU percentage

### Solver Statistics (if available)
- Conflicts, decisions, propagations
- Restarts
- Learnt literals and clauses
- Decision heights
- And more...

### Computed Metrics
- PAR-2 score (2× timeout for unsolved)
- Clause/variable ratio
- Benchmark difficulty classification

## 🔧 Advanced Usage

### Custom Metrics

To add custom metrics to your runs, edit `app/core/database.py` and add columns to the `runs` table.

### Custom Parsers

Add solver-specific output parsers in `app/utils/solver_detector.py` to extract additional metrics.

### Parallel Execution

Adjust `parallel_jobs` in experiment configuration:
- `1`: Sequential execution
- `> 1`: Parallel execution with multiprocessing
- Recommended: Number of CPU cores - 1

### Checkpointing

Experiments automatically checkpoint every 100 runs. To resume:
1. Go to experiment page
2. Click "Resume" on interrupted experiment

## 🐛 Troubleshooting

### Solver won't compile
- Check build dependencies (gcc, make, cmake, etc.)
- Review compilation logs in Setup page
- Try manual compilation first, then add as pre-compiled

### Benchmark not loading
- Ensure file is valid CNF format
- Check file permissions
- Look for "p cnf" line in file header

### Database errors
- Check `results/` directory permissions
- Delete `experiments.db` to recreate (loses data!)
- Check SQLite is accessible

### Out of memory during experiments
- Reduce `parallel_jobs`
- Lower `memory_limit_mb`
- Filter benchmarks to smaller instances

## 📝 Best Practices

1. **Start Small**: Test with 10-20 benchmarks before large experiments
2. **Document**: Add descriptions to experiments for future reference
3. **Backup**: Export results regularly
4. **Monitor**: Watch system resources during experiments
5. **Validate**: Test solvers individually before batch runs
6. **Compare Incrementally**: Add one solver at a time

## 🤝 Contributing

This is a research tool. Contributions welcome:
- Add new solver templates
- Improve statistical analysis
- Add visualization types
- Optimize database queries

## 📄 License

For academic and research use.

## 🙏 Acknowledgments

Built for SAT solver research and benchmarking. Supports standard SAT competition formats.

## 📧 Support

For issues and questions, refer to the in-app FAQ or check the logs in the console.

---

**Happy Benchmarking! 🚀**
