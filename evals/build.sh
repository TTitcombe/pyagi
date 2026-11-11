#!/bin/bash
# Build the shared base world, then every overlay on top of it. Run after any change under evals/base or evals/overlays.
set -euo pipefail
cd "$(dirname "$0")"

docker build -q -t pyagi-evals-base:local base
for overlay in overlays/*/; do
  name=$(basename "$overlay")
  docker build -q -t "pyagi-evals-$name:local" "$overlay"
done
