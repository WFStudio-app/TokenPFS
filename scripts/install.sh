#!/usr/bin/env bash
# ============================================================
#  TokenPFS — one-click auto installer
#  Usage: curl -fsSL https://raw.githubusercontent.com/WFStudio-app/TokenPFS/main/scripts/install.sh | bash
#  Supports: Linux (apt/dnf/pacman/zypper), Termux (Android), macOS (Homebrew),
#            VPS/cloud servers over SSH (headless, no desktop needed)
#  Windows users: use scripts/install.ps1 instead (PowerShell).
# ============================================================
set -e

REPO_URL="https://github.com/WFStudio-app/TokenPFS.git"
INSTALL_DIR="${TOKENPFS_HOME:-$HOME/.tokenpfs/TokenPFS}"
BIN_DIR="$HOME/.local/bin"

say()   { printf "\033[1;36m==>\033[0m %s\n" "$*"; }
ok()    { printf "\033[1;32m[OK]\033[0m %s\n" "$*"; }
warn()  { printf "\033[1;33m[!]\033[0m %s\n" "$*"; }
fail()  { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*"; exit 1; }

# ---------- detect platform ----------
IS_TERMUX=false
[ -n "$PREFIX" ] && case "$PREFIX" in *com.termux*) IS_TERMUX=true ;; esac
OS="$(uname -s)"

# SUDO handling: root on VPS/minimal images has no sudo binary
SUDO=""
if [ "$(id -u)" != "0" ]; then
    if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; else
        fail "Not root and sudo not found — run as root (typical on VPS: ssh root@server)."
    fi
fi

# VPS / headless detection (informational)
IS_VPS=false
{ [ -f /.dockerenv ] || [ -f /run/systemd/container ] || \
  grep -qi 'hypervisor' /proc/cpuinfo 2>/dev/null; } && IS_VPS=true
say "Platform: $OS$( [ "$IS_TERMUX" = true ] && echo ' (Termux)' )$( [ "$IS_VPS" = true ] && echo ' (virtualized/VPS — headless OK)' )"

# ---------- install dependencies ----------
if [ "$IS_TERMUX" = true ]; then
    say "Installing via pkg (python, git, curl, ollama)..."
    pkg update -y >/dev/null
    pkg install -y python git curl tar ollama >/dev/null || warn "ollama pkg failed — will use DEMO mode"
elif command -v apt-get >/dev/null 2>&1; then
    $SUDO apt-get update -y >/dev/null && $SUDO apt-get install -y python3 git curl >/dev/null
elif command -v dnf >/dev/null 2>&1; then
    $SUDO dnf install -y python3 git curl >/dev/null
elif command -v yum >/dev/null 2>&1; then
    $SUDO yum install -y python3 git curl >/dev/null
elif command -v pacman >/dev/null 2>&1; then
    $SUDO pacman -S --noconfirm python git curl >/dev/null
elif command -v zypper >/dev/null 2>&1; then
    $SUDO zypper -n install python3 git curl >/dev/null
elif command -v apk >/dev/null 2>&1; then
    $SUDO apk add --no-cache python3 git curl >/dev/null
elif [ "$OS" = "Darwin" ]; then
    command -v brew >/dev/null 2>&1 || fail "Install Homebrew first: https://brew.sh"
    brew list python &>/dev/null || brew install python
    brew list git   &>/dev/null || brew install git
else
    fail "No supported package manager found. Install python3+git manually and re-run."
fi
ok "Dependencies ready: $(python3 --version 2>/dev/null || python --version)"

# ---------- install Ollama (skip on Termux if pkg already provided it) ----------
if ! command -v ollama >/dev/null 2>&1; then
    if [ "$OS" = "Darwin" ]; then
        brew list ollama &>/dev/null || brew install ollama
    elif [ "$IS_TERMUX" != true ]; then
        say "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh || warn "Ollama install failed — TokenPFS will run in DEMO mode"
    fi
fi
if command -v ollama >/dev/null 2>&1; then
    ok "Ollama: $(ollama --version 2>/dev/null | head -1)"
    # start server if not running
    if ! curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        say "Starting Ollama server in background..."
        nohup ollama serve >/tmp/ollama.log 2>&1 &
        sleep 2
    fi
else
    warn "Ollama unavailable — TokenPFS will start in DEMO mode"
fi

# ---------- fetch TokenPFS ----------
say "Downloading TokenPFS to $INSTALL_DIR ..."
if [ -d "$INSTALL_DIR/.git" ]; then
    git -C "$INSTALL_DIR" pull --ff-only >/dev/null && ok "Updated existing installation"
else
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR" >/dev/null && ok "Cloned repository"
fi

# ---------- launcher ----------
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/tokenpfs" << LAUNCH
#!/usr/bin/env bash
cd "$INSTALL_DIR"
exec python3 tokenpfs_app.py "\$@"
LAUNCH
chmod +x "$BIN_DIR/tokenpfs"
ok "Launcher created: $BIN_DIR/tokenpfs"

# ensure PATH contains ~/.local/bin
RC="$HOME/.bashrc"; [ "$IS_TERMUX" = true ] && RC="$PREFIX/../.bashrc"
if ! echo "$PATH" | grep -q "$BIN_DIR"; then
    grep -q '.local/bin' "$RC" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RC"
    warn "Added ~/.local/bin to PATH in $RC (open a new terminal or: source $RC)"
fi

echo
printf "\033[1;32m============================================================\033[0m\n"
printf "  \033[1mTokenPFS installed!\033[0m\n\n"
printf "  Run it:      \033[1;36mtokenpfs\033[0m\n"
printf "  First steps: /models  ->  /dl 01  ->  /w 01 <question>\n"
printf "  Auto-tune:   /autt     (measures your hardware)\n"
printf "\033[1;32m============================================================\033[0m\n"
