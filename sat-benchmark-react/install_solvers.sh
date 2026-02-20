#!/usr/bin/env bash
# ================================================================
# install_solvers.sh — Install SAT solvers for the benchmark suite
# ================================================================
#
# Usage:
#   ./install_solvers.sh                  # install all solvers
#   ./install_solvers.sh kissat cadical   # install specific ones
#   ./install_solvers.sh --list           # show available solvers
#   ./install_solvers.sh --status         # show installed status
#
# ================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOLVERS_DIR="${SOLVERS_DIR:-$SCRIPT_DIR/solvers}"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 2)}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

log()   { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[  OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[FAIL]${NC} $*"; }
header(){ echo -e "\n${BOLD}${CYAN}==> $*${NC}"; }

# ── System dependency check ────────────────────────────

check_deps() {
    local missing=()
    for cmd in git make gcc g++ cmake; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        warn "Missing tools: ${missing[*]}"
        echo "  Install them with:"
        echo "    sudo apt-get install build-essential cmake git zlib1g-dev"
        return 1
    fi
    ok "All build tools found"
    return 0
}

# ── Kissat ──────────────────────────────────────────────

install_kissat() {
    header "Installing Kissat"
    local dir="$SOLVERS_DIR/kissat"

    if [[ -x "$dir/build/kissat" ]]; then
        ok "Kissat already installed: $("$dir/build/kissat" --version 2>&1 | head -1)"
        return 0
    fi

    if [[ ! -d "$dir" ]]; then
        log "Cloning Kissat..."
        git clone --depth 1 https://github.com/arminbiere/kissat.git "$dir"
    fi

    cd "$dir"
    log "Configuring..."
    ./configure
    log "Building (jobs=$JOBS)..."
    make -j"$JOBS"

    if [[ -x "build/kissat" ]]; then
        ok "Kissat installed: $(build/kissat --version 2>&1 | head -1)"
    else
        err "Kissat build failed — binary not found"
        return 1
    fi
}

# ── MiniSat ─────────────────────────────────────────────

install_minisat() {
    header "Installing MiniSat"
    local dir="$SOLVERS_DIR/minisat"

    if [[ -x "$dir/core/minisat" ]] || [[ -x "$dir/simp/minisat" ]]; then
        ok "MiniSat already installed"
        return 0
    fi

    if [[ ! -d "$dir" ]]; then
        log "Cloning MiniSat..."
        git clone --depth 1 https://github.com/niklasso/minisat.git "$dir"
    fi

    cd "$dir"
    log "Building core..."
    if ! make -C core rs 2>/dev/null; then
        log "Release build failed, trying default..."
        make -C core || true
    fi

    if [[ -x "core/minisat" ]]; then
        ok "MiniSat (core) installed"
    elif [[ -x "simp/minisat" ]]; then
        ok "MiniSat (simp) installed"
    else
        err "MiniSat build failed"
        return 1
    fi
}

# ── CaDiCaL ─────────────────────────────────────────────

install_cadical() {
    header "Installing CaDiCaL"
    local dir="$SOLVERS_DIR/cadical"

    if [[ -x "$dir/build/cadical" ]]; then
        ok "CaDiCaL already installed: $("$dir/build/cadical" --version 2>&1 | head -1)"
        return 0
    fi

    if [[ ! -d "$dir" ]]; then
        log "Cloning CaDiCaL..."
        git clone --depth 1 https://github.com/arminbiere/cadical.git "$dir"
    fi

    cd "$dir"
    log "Configuring..."
    ./configure
    log "Building (jobs=$JOBS)..."
    make -j"$JOBS"

    if [[ -x "build/cadical" ]]; then
        ok "CaDiCaL installed: $(build/cadical --version 2>&1 | head -1)"
    else
        err "CaDiCaL build failed — binary not found"
        return 1
    fi
}

# ── CryptoMiniSat ───────────────────────────────────────

install_cryptominisat() {
    header "Installing CryptoMiniSat"
    local dir="$SOLVERS_DIR/cryptominisat"

    if [[ -x "$dir/build/cryptominisat5" ]]; then
        ok "CryptoMiniSat already installed: $("$dir/build/cryptominisat5" --version 2>&1 | head -1)"
        return 0
    fi

    # Extra deps check
    if ! command -v cmake &>/dev/null; then
        err "CryptoMiniSat requires cmake"
        return 1
    fi

    if [[ ! -d "$dir" ]]; then
        log "Cloning CryptoMiniSat..."
        git clone --depth 1 https://github.com/msoos/cryptominisat.git "$dir"
    fi

    cd "$dir"
    log "Initialising submodules..."
    git submodule update --init 2>/dev/null || true

    mkdir -p build && cd build
    log "Running cmake..."
    if ! cmake -DCMAKE_BUILD_TYPE=Release .. 2>/dev/null; then
        warn "cmake with defaults failed, trying minimal config..."
        cmake -DCMAKE_BUILD_TYPE=Release -DNOM4RI=ON -DSTATS=OFF -DENABLE_TESTING=OFF ..
    fi

    log "Building (jobs=$JOBS)..."
    make -j"$JOBS"

    if [[ -x "cryptominisat5" ]]; then
        ok "CryptoMiniSat installed: $(./cryptominisat5 --version 2>&1 | head -1)"
    else
        err "CryptoMiniSat build failed — binary not found"
        return 1
    fi
}

# ── Status ──────────────────────────────────────────────

show_status() {
    header "Solver Status"
    local solvers=("kissat:build/kissat" "minisat:core/minisat" "cadical:build/cadical" "cryptominisat:build/cryptominisat5")

    printf "  %-18s %-12s %s\n" "SOLVER" "STATUS" "PATH"
    printf "  %-18s %-12s %s\n" "------" "------" "----"

    for entry in "${solvers[@]}"; do
        local name="${entry%%:*}"
        local bin="${entry##*:}"
        local path="$SOLVERS_DIR/$name/$bin"

        if [[ -x "$path" ]]; then
            local ver
            ver=$("$path" --version 2>&1 | head -1 || echo "?")
            printf "  ${GREEN}%-18s${NC} %-12s %s\n" "$name" "ready ($ver)" "$path"
        elif [[ -d "$SOLVERS_DIR/$name" ]]; then
            printf "  ${YELLOW}%-18s${NC} %-12s %s\n" "$name" "not built" "$SOLVERS_DIR/$name"
        else
            printf "  ${RED}%-18s${NC} %-12s %s\n" "$name" "not installed" "-"
        fi
    done
}

# ── Main ────────────────────────────────────────────────

ALL_SOLVERS=(kissat minisat cadical cryptominisat)

show_list() {
    echo "Available solvers:"
    for s in "${ALL_SOLVERS[@]}"; do
        echo "  - $s"
    done
}

main() {
    echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║   SAT Benchmark Suite — Solver Installer ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"

    case "${1:-}" in
        --list|-l)   show_list; exit 0 ;;
        --status|-s) show_status; exit 0 ;;
        --help|-h)
            echo "Usage: $0 [solver1 solver2 ...] | --list | --status | --help"
            exit 0
            ;;
    esac

    check_deps || exit 1
    mkdir -p "$SOLVERS_DIR"

    local targets=("$@")
    if [[ ${#targets[@]} -eq 0 ]]; then
        targets=("${ALL_SOLVERS[@]}")
    fi

    local ok_count=0
    local fail_count=0

    for solver in "${targets[@]}"; do
        case "$solver" in
            kissat)         install_kissat         && ((ok_count++)) || ((fail_count++)) ;;
            minisat)        install_minisat         && ((ok_count++)) || ((fail_count++)) ;;
            cadical)        install_cadical         && ((ok_count++)) || ((fail_count++)) ;;
            cryptominisat)  install_cryptominisat   && ((ok_count++)) || ((fail_count++)) ;;
            *)
                warn "Unknown solver: $solver"
                ((fail_count++))
                ;;
        esac
    done

    echo ""
    show_status
    echo ""

    if [[ $fail_count -gt 0 ]]; then
        warn "$ok_count succeeded, $fail_count failed"
        exit 1
    else
        ok "All $ok_count solvers installed successfully!"
    fi
}

main "$@"
