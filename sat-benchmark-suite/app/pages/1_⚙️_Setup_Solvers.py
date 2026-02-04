"""
Solver Setup and Management Page
Upload, compile, and manage SAT solvers
"""

import streamlit as st
import sys
from pathlib import Path
import json
import shutil
import subprocess
import os
import tempfile
import zipfile
import tarfile



# Add parent directory to path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from core.database import DatabaseManager
from utils.helpers import format_time, get_system_info
import logging

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Setup Solvers", page_icon="⚙️", layout="wide")

# Initialize database
@st.cache_resource
def init_db():
    return DatabaseManager("results/experiments.db")

db = init_db()

# Load solver templates
@st.cache_data
def load_solver_templates():
    template_path = Path("config/solver_templates.json")
    if template_path.exists():
        with open(template_path, 'r') as f:
            return json.load(f)
    return {}

solver_templates = load_solver_templates()

# Header
st.title("⚙️ Solver Setup & Management")
st.markdown("Upload, compile, and manage your SAT solvers")

st.markdown("---")

# Tabs for different operations
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Current Solvers", 
    "➕ Add Solver", 
    "🔨 Compile Solver",
    "🗑️ Manage"
])

# ==================== TAB 1: Current Solvers ====================
with tab1:
    st.header("Registered Solvers")
    
    solvers = db.get_solvers()
    
    if not solvers:
        st.info("No solvers registered yet. Add a solver in the 'Add Solver' tab.")
    else:
        # Filter options
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            status_filter = st.selectbox(
                "Filter by status",
                ["All", "ready", "needs_compile", "error"],
                key="status_filter"
            )
        with col2:
            search_term = st.text_input("Search solver name", key="search_solver")
        with col3:
            st.write("")
            st.write("")
            if st.button("🔄 Refresh", key="refresh_solvers"):
                st.cache_data.clear()
                st.rerun()
        
        # Filter solvers
        filtered_solvers = solvers
        if status_filter != "All":
            filtered_solvers = [s for s in filtered_solvers if s['status'] == status_filter]
        if search_term:
            filtered_solvers = [s for s in filtered_solvers if search_term.lower() in s['name'].lower()]
        
        st.markdown(f"**Showing {len(filtered_solvers)} of {len(solvers)} solvers**")
        
        # Display solvers in cards
        for solver in filtered_solvers:
            with st.expander(f"🔧 **{solver['name']}** - {solver['status'].upper()}", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Version:** {solver['version'] or 'Unknown'}")
                    st.markdown(f"**Executable:** `{solver['executable_path']}`")
                    st.markdown(f"**Source Path:** `{solver['source_path'] or 'N/A'}`")
                    st.markdown(f"**Status:** {solver['status']}")
                    
                    if solver['last_compiled']:
                        st.markdown(f"**Last Compiled:** {solver['last_compiled']}")
                    
                    # Test solver
                    if solver['status'] == 'ready':
                        if st.button(f"🧪 Test {solver['name']}", key=f"test_{solver['id']}"):
                            try:
                                exe_path = Path(solver['executable_path'])
                                if exe_path.exists():
                                    result = subprocess.run(
                                        [str(exe_path), "--version"],
                                        capture_output=True,
                                        text=True,
                                        timeout=5
                                    )
                                    if result.returncode == 0 or result.stdout or result.stderr:
                                        st.success(f"✅ {solver['name']} is working!")
                                        with st.code_block():
                                            st.text(result.stdout or result.stderr)
                                    else:
                                        st.warning(f"Solver responded but with exit code {result.returncode}")
                                else:
                                    st.error(f"Executable not found at {exe_path}")
                            except Exception as e:
                                st.error(f"Error testing solver: {e}")
                
                with col2:
                    # Status badge
                    if solver['status'] == 'ready':
                        st.success("✅ Ready to use")
                    elif solver['status'] == 'needs_compile':
                        st.warning("⚠️ Needs compilation")
                    else:
                        st.error("❌ Error")
                    
                    # Actions
                    st.markdown("**Actions:**")
                    if st.button("🗑️ Delete", key=f"delete_{solver['id']}"):
                        # Note: We'll implement deletion in the Manage tab
                        st.warning("Use the Manage tab to delete solvers")

# ==================== TAB 2: Add Solver ====================
with tab2:
    st.header("Add New Solver")
    
    # Method selection
    add_method = st.radio(
        "How would you like to add a solver?",
        ["📦 Upload Archive (ZIP/TAR.GZ)", "📁 Local Directory", "⚡ Quick Add (Pre-compiled)"],
        key="add_method"
    )
    
    st.markdown("---")
    
    # Method 1: Upload Archive
    if add_method == "📦 Upload Archive (ZIP/TAR.GZ)":
        st.markdown("""
        Upload a ZIP or TAR.GZ file containing the solver source code. 
        The system will auto-detect the build system and compile it.
        """)
        
        uploaded_file = st.file_uploader(
            "Choose solver archive",
            type=['zip', 'tar', 'gz', 'tgz'],
            key="solver_upload"
        )
        
        solver_name = st.text_input("Solver Name", key="upload_solver_name")
        
        col1, col2 = st.columns(2)
        with col1:
            auto_detect = st.checkbox("Auto-detect build system", value=True, key="auto_detect")
        with col2:
            solver_template = st.selectbox(
                "Or select template",
                ["None"] + list(solver_templates.keys()),
                key="solver_template"
            )
        
        if not auto_detect and solver_template == "None":
            build_commands = st.text_area(
                "Build commands (one per line)",
                placeholder="cd core\nmake",
                key="custom_build_commands"
            )
            executable_path = st.text_input(
                "Relative path to executable",
                placeholder="core/minisat",
                key="custom_executable"
            )
        
        if st.button("📤 Upload and Extract", key="upload_extract", type="primary"):
            if not uploaded_file or not solver_name:
                st.error("Please provide both a file and solver name")
            else:
                with st.spinner("Extracting solver..."):
                    try:
                        # Create solver directory
                        solver_dir = Path(f"solvers/{solver_name}")
                        solver_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Save uploaded file
                        temp_file = Path(f"temp/{uploaded_file.name}")
                        temp_file.parent.mkdir(exist_ok=True)
                        
                        with open(temp_file, 'wb') as f:
                            f.write(uploaded_file.read())
                        
                        # Extract archive
                        if uploaded_file.name.endswith('.zip'):
                            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                                zip_ref.extractall(solver_dir)
                        elif uploaded_file.name.endswith(('.tar.gz', '.tgz', '.tar')):
                            with tarfile.open(temp_file, 'r:*') as tar_ref:
                                tar_ref.extractall(solver_dir)
                        
                        st.success(f"✅ Extracted to {solver_dir}")
                        
                        # Auto-detect or use template
                        detected_info = None
                        if auto_detect:
                            st.info("🔍 Auto-detecting build system...")
                            # Look for common build files
                            for name, template in solver_templates.items():
                                for build_file in template.get('build_files', []):
                                    if (solver_dir / build_file).exists():
                                        detected_info = template
                                        st.success(f"✅ Detected: {template['name']}")
                                        break
                                if detected_info:
                                    break
                        elif solver_template != "None":
                            detected_info = solver_templates[solver_template]
                        
                        # Add to database
                        if detected_info:
                            # Find executable (will be set after compilation)
                            exe_path = f"solvers/{solver_name}/pending"
                            
                            db.add_solver(
                                name=solver_name,
                                executable_path=exe_path,
                                source_path=str(solver_dir),
                                compile_command="\n".join(detected_info.get('build_commands', [])),
                                status='needs_compile',
                                metadata=detected_info
                            )
                            
                            st.success(f"✅ Added {solver_name} to database. Go to 'Compile Solver' tab to build it.")
                        else:
                            st.warning("Could not auto-detect build system. Please configure manually.")
                        
                        # Clean up temp file
                        temp_file.unlink()
                        
                    except Exception as e:
                        st.error(f"Error extracting solver: {e}")
                        logger.error(f"Extraction error: {e}", exc_info=True)
    
    # Method 2: Local Directory
    elif add_method == "📁 Local Directory":
        st.markdown("""
        Point to an existing directory containing solver source code.
        """)
        
        local_path = st.text_input(
            "Path to solver directory",
            placeholder="C:/solvers/minisat",
            key="local_path"
        )
        
        solver_name = st.text_input("Solver Name", key="local_solver_name")
        
        if st.button("➕ Add from Directory", key="add_local", type="primary"):
            if not local_path or not solver_name:
                st.error("Please provide both path and solver name")
            elif not Path(local_path).exists():
                st.error(f"Directory not found: {local_path}")
            else:
                try:
                    db.add_solver(
                        name=solver_name,
                        executable_path=f"{local_path}/pending",
                        source_path=local_path,
                        status='needs_compile'
                    )
                    st.success(f"✅ Added {solver_name} from {local_path}")
                except Exception as e:
                    st.error(f"Error adding solver: {e}")
    
    # Method 3: Pre-compiled
    else:  # Quick Add
        st.markdown("""
        Add a pre-compiled solver by pointing directly to the executable.
        """)
        
        solver_name = st.text_input("Solver Name", key="quick_solver_name")
        executable_path = st.text_input(
            "Path to executable",
            placeholder="C:/solvers/minisat/core/minisat.exe",
            key="quick_executable"
        )
        
        version = st.text_input("Version (optional)", key="quick_version")
        
        if st.button("⚡ Add Pre-compiled Solver", key="add_quick", type="primary"):
            if not solver_name or not executable_path:
                st.error("Please provide both name and executable path")
            elif not Path(executable_path).exists():
                st.error(f"Executable not found: {executable_path}")
            else:
                try:
                    db.add_solver(
                        name=solver_name,
                        executable_path=executable_path,
                        version=version,
                        status='ready'
                    )
                    st.success(f"✅ Added pre-compiled {solver_name}")
                except Exception as e:
                    st.error(f"Error adding solver: {e}")

# ==================== TAB 3: Compile Solver ====================
with tab3:
    st.header("Compile Solver")
    
    # Get solvers that need compilation
    uncompiled = [s for s in db.get_solvers() if s['status'] == 'needs_compile']
    
    if not uncompiled:
        st.info("All solvers are compiled. Add a new solver to compile it.")
    else:
        st.markdown(f"**{len(uncompiled)} solver(s) need compilation**")
        
        solver_to_compile = st.selectbox(
            "Select solver to compile",
            options=[s['name'] for s in uncompiled],
            key="compile_solver_select"
        )
        
        if solver_to_compile:
            solver = next(s for s in uncompiled if s['name'] == solver_to_compile)
            
            st.markdown(f"**Source Path:** `{solver['source_path']}`")
            
            # Show build commands
            if solver['compile_command']:
                st.markdown("**Build Commands:**")
                st.code(solver['compile_command'], language="bash")
            
            # Option to edit commands
            with st.expander("✏️ Edit Build Commands"):
                custom_commands = st.text_area(
                    "Modify build commands if needed",
                    value=solver['compile_command'] or "",
                    height=150,
                    key="edit_commands"
                )
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("🔨 Compile Now", type="primary", key="compile_now"):
                    st.session_state.compiling = True
            
            # Compilation process
            if st.session_state.get('compiling', False):
                st.markdown("---")
                st.subheader("🔨 Compilation in Progress")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                log_container = st.container()
                
                try:
                    commands = (custom_commands if 'custom_commands' in locals() 
                               else solver['compile_command']).split('\n')
                    
                    with log_container:
                        st.markdown("**Compilation Log:**")
                        log_area = st.empty()
                        full_log = []
                        
                        for i, cmd in enumerate(commands):
                            if not cmd.strip():
                                continue
                            
                            status_text.info(f"Running: {cmd}")
                            progress_bar.progress((i + 1) / len(commands))
                            
                            # Run command
                            result = subprocess.run(
                                cmd,
                                shell=True,
                                cwd=solver['source_path'],
                                capture_output=True,
                                text=True,
                                timeout=300  # 5 minutes per command
                            )
                            
                            full_log.append(f"$ {cmd}")
                            full_log.append(result.stdout)
                            if result.stderr:
                                full_log.append(f"STDERR: {result.stderr}")
                            full_log.append("")
                            
                            log_area.code("\n".join(full_log))
                            
                            if result.returncode != 0:
                                st.error(f"❌ Command failed with exit code {result.returncode}")
                                db.update_solver_status(solver['id'], 'error')
                                st.session_state.compiling = False
                                st.stop()
                        
                        # Find executable
                        st.info("🔍 Looking for executable...")
                        metadata = json.loads(solver['metadata']) if solver['metadata'] else {}
                        exe_patterns = metadata.get('executable_patterns', [])
                        
                        found_exe = None
                        source_path = Path(solver['source_path'])
                        
                        for pattern in exe_patterns:
                            potential_exe = source_path / pattern
                            if potential_exe.exists():
                                found_exe = str(potential_exe)
                                break
                        
                        if not found_exe:
                            # Search for any executable
                            st.warning("Executable pattern not found, searching...")
                            for exe_file in source_path.rglob("*"):
                                if exe_file.is_file() and os.access(exe_file, os.X_OK):
                                    if solver['name'].lower() in exe_file.name.lower():
                                        found_exe = str(exe_file)
                                        break
                        
                        if found_exe:
                            db.update_solver_status(
                                solver['id'],
                                'ready',
                                executable_path=found_exe,
                                last_compiled=st.session_state.get('compile_time', 'now')
                            )
                            st.success(f"✅ Compilation successful! Executable: {found_exe}")
                        else:
                            st.error("❌ Compilation completed but executable not found")
                            db.update_solver_status(solver['id'], 'error')
                        
                        st.session_state.compiling = False
                        st.rerun()
                        
                except subprocess.TimeoutExpired:
                    st.error("❌ Compilation timed out (5 minutes)")
                    db.update_solver_status(solver['id'], 'error')
                    st.session_state.compiling = False
                except Exception as e:
                    st.error(f"❌ Compilation error: {e}")
                    logger.error(f"Compilation error: {e}", exc_info=True)
                    db.update_solver_status(solver['id'], 'error')
                    st.session_state.compiling = False

# ==================== TAB 4: Manage ====================
with tab4:
    st.header("Manage Solvers")
    
    st.markdown("### Bulk Operations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Delete All Error Solvers", key="delete_errors"):
            error_solvers = [s for s in db.get_solvers() if s['status'] == 'error']
            st.warning(f"This will delete {len(error_solvers)} solver(s) with error status")
            # Implementation needed
    
    with col2:
        if st.button("🔄 Recompile All", key="recompile_all"):
            st.info("This feature will be implemented in the next version")
    
    st.markdown("---")
    
    st.markdown("### Export/Import")
    
    if st.button("💾 Export Solver Configuration", key="export_config"):
        solvers = db.get_solvers()
        config = {
            'solvers': solvers,
            'export_date': str(datetime.now())
        }
        st.download_button(
            label="Download Config JSON",
            data=json.dumps(config, indent=2),
            file_name="solver_config.json",
            mime="application/json"
        )
