#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
./.venv/Scripts/python slip_gen_boundary.py
