#!/usr/bin/env bash
# Register the project kernel with Jupyter so notebooks open on the right
# interpreter.
#
# Why this is needed at all: the kernel.json that Jupyter/VS Code discovers
# inside the venv is a *data file shipped by the ipykernel wheel* (see its
# RECORD entry for ../../../share/jupyter/kernels/python3/kernel.json). That
# template hardcodes argv[0] as the bare string "python", which is not a
# command on this machine (`python` is absent from PATH; only python3 exists).
# Editors list the spec, fail to resolve the interpreter, and drop it from the
# picker again — the kernel "flashes and disappears".
#
# This script fixes both discovery paths:
#   1. ~/Library/Jupyter/kernels/arboili/  — a user-level spec with an absolute
#      interpreter path. Survives `uv sync` and venv rebuilds.
#   2. .venv/share/jupyter/kernels/python3/ — rewrites the ipykernel-shipped
#      spec in place so the venv entry stops flickering too. Ephemeral: any
#      `uv sync --reinstall-package ipykernel` restores the broken template,
#      which is why this script exists rather than a one-off manual edit.
#
# Usage:  scripts/install_kernel.sh        # from anywhere
# Re-run: after `uv sync --reinstall-package ipykernel` or any venv rebuild.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$ROOT/.venv/bin/python"
USER_KERNEL_DIR="${HOME}/Library/Jupyter/kernels/arboili"
VENV_KERNEL_DIR="$ROOT/.venv/share/jupyter/kernels/python3"

if [ ! -x "$VENV_PY" ]; then
  echo "No interpreter at $VENV_PY — run 'uv sync' first." >&2
  exit 1
fi

# Both specs get the absolute interpreter path and the same display name, so
# the two discovery paths are indistinguishable in the kernel picker.
"$VENV_PY" - "$VENV_PY" "$USER_KERNEL_DIR/kernel.json" "$VENV_KERNEL_DIR/kernel.json" <<'PY'
import json
import pathlib
import sys

python, *targets = sys.argv[1:]
spec = {
    "argv": [
        python,
        "-Xfrozen_modules=off",
        "-m",
        "ipykernel_launcher",
        "-f",
        "{connection_file}",
    ],
    "display_name": "Python (arboili · uv)",
    "language": "python",
    "metadata": {"debugger": True, "supported_encryption": "curve"},
    "kernel_protocol_version": "5.5",
}
for target in targets:
    path = pathlib.Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {path}")
PY

# Reuse the logos ipykernel already ships, so the user-level spec is not
# icon-less in the picker.
for logo in "$VENV_KERNEL_DIR"/logo-*; do
  [ -e "$logo" ] && cp "$logo" "$USER_KERNEL_DIR/"
done

echo
echo "Registered kernels:"
"$VENV_PY" -m jupyter kernelspec list
