#!/usr/bin/env bash
# Run from the project root: ./scripts/compile_protos.sh
# Requires: protoc (brew install protobuf  OR  conda install -c conda-forge protobuf)
set -euo pipefail

PROTO_OUT="backend/app/proto_gen"

echo "Compiling protos → $PROTO_OUT ..."

protoc \
  -I. \
  --python_out="$PROTO_OUT" \
  $(find proto -name "*.proto" | sort)

# Ensure Python packages exist at every generated directory level.
touch "$PROTO_OUT/__init__.py"
touch "$PROTO_OUT/proto/__init__.py"

echo "Done. Generated files:"
find "$PROTO_OUT" -name "*.py" | sort
