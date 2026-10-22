#!/usr/bin/env bash
# The former test counted theorem/axiom labels around sorry/Admitted and even
# swallowed Agda failure. That did not test preservation or proof validity.
# This admission regression requires explicit refusal of every unfaithful proof
# target and proves refusal neither creates artifacts nor overwrites user files.
# Actual source/native theorem checking is exercised by make certify-source.
set -euo pipefail
CORPUS_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
VERUM_BIN="${VERUM_BIN:-verum}"
TEST_DIR="$(mktemp -d "${TMPDIR:-/tmp}/msfs-export-admission.XXXXXX")"
trap 'rm -rf "$TEST_DIR"' EXIT
cd "$CORPUS_DIR"
for format in lean coq dedukti metamath agda; do
    output="$TEST_DIR/$format/proof.txt"
    log="$TEST_DIR/$format.log"
    if "$VERUM_BIN" export --to "$format" --with-provenance --output "$output" >"$log" 2>&1; then
        echo "FAIL: $format granted proof export without an exact typed translation" >&2
        exit 1
    fi
    if ! grep -q 'exact source statement' "$log"; then
        cat "$log" >&2
        echo "FAIL: $format failed for an unrelated reason" >&2
        exit 1
    fi
    test ! -e "$output"
    test ! -e "$output.provenance.json"
    mkdir -p "$(dirname "$output")"
    printf '%s\n' 'existing research artifact' > "$output"
    cp "$output" "$TEST_DIR/expected"
    if "$VERUM_BIN" export --to "$format" --with-provenance --output "$output" >"$log" 2>&1; then
        echo "FAIL: repeated export unexpectedly succeeded" >&2
        exit 1
    fi
    grep -q 'exact source statement' "$log"
    cmp "$output" "$TEST_DIR/expected"
    test ! -e "$output.provenance.json"
done
echo 'PASS: 5 explicit unsupported targets; no generated scaffolds; existing artifacts preserved.'
