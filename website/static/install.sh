#!/bin/sh

set -eu

UV_INSTALLER_URL="https://astral.sh/uv/install.sh"

find_uv() {
    if command -v uv >/dev/null 2>&1; then
        command -v uv
        return
    fi

    if [ -n "${UV_INSTALL_DIR:-}" ] && [ -x "$UV_INSTALL_DIR/uv" ]; then
        printf '%s\n' "$UV_INSTALL_DIR/uv"
        return
    fi
    if [ -n "${XDG_BIN_HOME:-}" ] && [ -x "$XDG_BIN_HOME/uv" ]; then
        printf '%s\n' "$XDG_BIN_HOME/uv"
        return
    fi

    for candidate in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv"; do
        if [ -x "$candidate" ]; then
            printf '%s\n' "$candidate"
            return
        fi
    done

    return 1
}

uv_bin=$(find_uv || true)
if [ -z "$uv_bin" ]; then
    printf '%s\n' "Je uses uv to manage its isolated Python environment."
    printf '%s\n' "uv was not found, so the official uv installer will be run now."

    if command -v curl >/dev/null 2>&1; then
        curl -LsSf "$UV_INSTALLER_URL" | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- "$UV_INSTALLER_URL" | sh
    else
        printf '%s\n' "Error: installing uv requires curl or wget." >&2
        exit 1
    fi

    uv_bin=$(find_uv || true)
    if [ -z "$uv_bin" ]; then
        printf '%s\n' "Error: uv was installed but its executable could not be found." >&2
        printf '%s\n' "Open a new terminal and run: uv tool install git+https://github.com/JeffreyLei03/JE.git" >&2
        exit 1
    fi
fi

printf '%s\n' "Installing Je with $uv_bin ..."
"$uv_bin" tool install git+https://github.com/JeffreyLei03/JE.git

tool_bin=$("$uv_bin" tool dir --bin)
je_bin="$tool_bin/je"
if [ ! -x "$je_bin" ]; then
    printf '%s\n' "Error: Je was installed but $je_bin was not found." >&2
    exit 1
fi

"$je_bin" --version
printf '%s\n' "Je is installed. Run: je"

case ":$PATH:" in
    *":$tool_bin:"*) ;;
    *)
        printf '%s\n' "Restart your shell if 'je' is not found; $tool_bin must be on PATH."
        ;;
esac
