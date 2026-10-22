# =============================================================================
# verum-corpus Makefile — MSFS machine-verification CI / build / audit shortcuts
# =============================================================================
#
# Single entry point for every operation a reviewer or maintainer might
# perform on this corpus.  Run `make help` for the full target list.
#
#   • `make`                   — full green-light pipeline (check + audit + gate)
#   • `make check`             — type-check the corpus
#   • `make verify`            — run the verification ladder
#   • `make audit`             — emit every audit report into audit-reports/
#   • `make audit-msfs`        — MSFS-specific audits (htt, ar, self-recognition)
#   • `make export`            — emit foreign-format certificates
#   • `make help`              — human-readable list of targets
# =============================================================================

VERUM           ?= verum
# Stdlib resolution: the corpus tracks the live language stdlib (sibling
# repo). Two env vars, two subsystems:
#   VERUM_STDLIB_PATH — module-registry population for `verum check`
#       (Normal mode otherwise uses the binary's embedded archive, which
#       bakes only the runtime prelude — core.math.* file modules like
#       absolute_layer / s_definable.lemma_3_4 are NOT in it, so every
#       corpus mount would fail with E402).  First source-driven run is
#       slow (full stdlib parse), later runs hit the disk cache.
#   VERUM_CORE_PATH — kernel/prove-path core source resolution.
# Point both at the live tree; without them the CLI falls back to
# embedded/stale snapshots and the corpus silently drops out of check.
export VERUM_STDLIB_PATH ?= $(abspath $(CURDIR)/../../verum-lang/verum/core)
export VERUM_CORE_PATH ?= $(abspath $(CURDIR)/../../verum-lang/verum/core)
#   VERUM_STDLIB_ROOT — the audit subsystem's stdlib walker (apply-graph,
#       framework-footprint, …): without it every stdlib-side axiom shows
#       up as an `unresolved` apply-graph leaf and L4 verdicts are noise.
export VERUM_STDLIB_ROOT ?= $(abspath $(CURDIR)/../../verum-lang/verum/core)
PYTHON          ?= python3
AUDIT_DIR       ?= audit-reports
JSON_FORMAT     := --format json

.DEFAULT_GOAL := default

# -----------------------------------------------------------------------------
# Default target: type-check + audit + honesty gate (CI green-light bundle)
# -----------------------------------------------------------------------------
.PHONY: default
default: check audit-honesty-gate

.PHONY: help
help:
	@echo "verum-corpus targets:"
	@echo ""
	@echo "  make / make default            full CI green-light bundle"
	@echo "  make check                     verum check (type-check)"
	@echo "  make verify                    verum verify (full ladder)"
	@echo "  make smoke                     run smoke test suite"
	@echo "  make export                    emit foreign-format certificates"
	@echo ""
	@echo "  make audit                     all audit reports → audit-reports/"
	@echo "  make audit-msfs                MSFS-scope audit bundle (htt-roadmap,"
	@echo "                                 ar-roadmap, self-recognition,"
	@echo "                                 cross-format, kernel-intrinsics)"
	@echo "  make audit-msfs-summary        live human-readable MSFS audit"
	@echo "  make audit-honesty             proof-honesty live audit"
	@echo "  make audit-honesty-gate        proof-honesty CI gate"
	@echo "  make refresh-honesty-baseline  raise the honesty floor"
	@echo ""
	@echo "  make clean                     remove build artefacts"

# -----------------------------------------------------------------------------
# Type-checking + verification
# -----------------------------------------------------------------------------
.PHONY: check
check:
	@echo "▶ verum check"
	@$(VERUM) check

.PHONY: verify
verify:
	@echo "▶ verum verify"
	@$(VERUM) verify

# -----------------------------------------------------------------------------
# Audit reports — generic and MSFS-specific
# -----------------------------------------------------------------------------
.PHONY: audit
audit: audit-coord audit-framework audit-accessibility audit-coherent \
       audit-framework-soundness audit-coord-consistency \
       audit-hygiene-strict audit-honesty audit-msfs

.PHONY: audit-msfs
audit-msfs: audit-htt-roadmap audit-ar-roadmap audit-self-recognition \
            audit-cross-format audit-kernel-intrinsics
	@echo ""
	@echo "▶ MSFS-scope audit bundle complete — see $(AUDIT_DIR)/{htt,ar,self-recognition,cross-format,kernel-intrinsics}.json"

# Live human-readable summary of the MSFS-scope audits (no JSON files).
.PHONY: audit-msfs-summary
audit-msfs-summary:
	@$(VERUM) audit --htt-roadmap
	@echo ""
	@$(VERUM) audit --ar-roadmap
	@echo ""
	@$(VERUM) audit --kernel-soundness

# -- Generic audits ----------------------------------------------------------

.PHONY: audit-coord
audit-coord:
	@$(VERUM) audit --coord $(JSON_FORMAT) > $(AUDIT_DIR)/coord.json

.PHONY: audit-framework
audit-framework:
	@$(VERUM) audit --framework-axioms $(JSON_FORMAT) > $(AUDIT_DIR)/framework-footprint.json

.PHONY: audit-accessibility
audit-accessibility:
	@$(VERUM) audit --accessibility $(JSON_FORMAT) > $(AUDIT_DIR)/accessibility.json

.PHONY: audit-coherent
audit-coherent:
	@$(VERUM) audit --coherent $(JSON_FORMAT) > $(AUDIT_DIR)/coherent.json

.PHONY: audit-framework-soundness
audit-framework-soundness:
	@$(VERUM) audit --framework-soundness $(JSON_FORMAT) > $(AUDIT_DIR)/framework-soundness.json
	@$(VERUM) audit --framework-soundness | tail -5

.PHONY: audit-coord-consistency
audit-coord-consistency:
	@$(VERUM) audit --coord-consistency $(JSON_FORMAT) > $(AUDIT_DIR)/coord-consistency.json
	@$(VERUM) audit --coord-consistency | tail -8

.PHONY: audit-hygiene-strict
audit-hygiene-strict:
	@$(VERUM) audit --hygiene-strict $(JSON_FORMAT) > $(AUDIT_DIR)/hygiene-strict.json
	@$(VERUM) audit --hygiene-strict | tail -5

# -- MSFS-scope audits -------------------------------------------------------

.PHONY: audit-htt-roadmap
audit-htt-roadmap:
	@$(VERUM) audit --htt-roadmap $(JSON_FORMAT) > $(AUDIT_DIR)/htt-roadmap.json
	@$(VERUM) audit --htt-roadmap | tail -3

.PHONY: audit-ar-roadmap
audit-ar-roadmap:
	@$(VERUM) audit --ar-roadmap $(JSON_FORMAT) > $(AUDIT_DIR)/ar-roadmap.json
	@$(VERUM) audit --ar-roadmap | tail -3

.PHONY: audit-self-recognition
audit-self-recognition:
	@# CLI drift note (2026-07-10): `--self-recognition` was removed from
	@# `verum audit`; `--kernel-soundness` is the current trusted-base
	@# surface (Rust-rule roster vs .vr corpus + Coq/Lean re-check files).
	@$(VERUM) audit --kernel-soundness $(JSON_FORMAT) > $(AUDIT_DIR)/self-recognition.json
	@$(VERUM) audit --kernel-soundness | tail -5

.PHONY: audit-cross-format
audit-cross-format:
	@$(VERUM) audit --cross-format $(JSON_FORMAT) > $(AUDIT_DIR)/cross-format.json
	@$(VERUM) audit --cross-format | tail -5

.PHONY: audit-kernel-intrinsics
audit-kernel-intrinsics:
	@$(VERUM) audit --kernel-intrinsics $(JSON_FORMAT) > $(AUDIT_DIR)/kernel-intrinsics.json
	@$(VERUM) audit --kernel-intrinsics | tail -3

.PHONY: audit-honesty
audit-honesty:
	@$(VERUM) audit --proof-honesty $(JSON_FORMAT) > $(AUDIT_DIR)/proof-honesty.json
	@$(VERUM) audit --proof-honesty | tail -10

# -----------------------------------------------------------------------------
# proof-honesty CI gate (regressions blocked)
# -----------------------------------------------------------------------------
# Compares live `verum audit --proof-honesty` against the frozen baseline in
# tests/proof_honesty_baseline.json.  Exits non-zero on any regression
# (more axiom-placeholder, fewer multi-step / structural, any new
# theorem-trivial-true or theorem-no-proof-body).

.PHONY: audit-honesty-gate
audit-honesty-gate:
	@VERUM_BIN=$(VERUM) bash tests/integration/proof_honesty_gate.sh

# Refresh the baseline to live counts (use after intentional upgrades).
.PHONY: refresh-honesty-baseline
refresh-honesty-baseline:
	@$(VERUM) audit --proof-honesty $(JSON_FORMAT) > $(AUDIT_DIR)/proof-honesty.json
	@echo "  (baseline refresh: hand-edit tests/proof_honesty_baseline.json after live audit)"

# -----------------------------------------------------------------------------
# Smoke / integration / regression test suites
# -----------------------------------------------------------------------------
.PHONY: smoke
smoke:
	@echo "▶ running smoke tests"
	@for f in tests/smoke/*.vr; do \
	  echo "  ▸ $$f"; \
	  $(VERUM) check $$f || exit 1; \
	done

.PHONY: integration
integration:
	@echo "▶ running integration shell scripts"
	@for f in tests/integration/*.sh; do \
	  echo "  ▸ $$f"; \
	  VERUM_BIN=$(VERUM) bash $$f || exit 1; \
	done

.PHONY: test
test: smoke integration

# -----------------------------------------------------------------------------
# Foreign-format certificate export
# -----------------------------------------------------------------------------
.PHONY: export
export:
	@# CLI drift note (2026-07-10): `--to agda` was removed from `verum
	@# export`, and --output now takes a FILE path (defaults to
	@# certificates/<format>/export.<ext>) rather than a directory.
	@echo "▶ exporting Coq / Lean / Dedukti / Metamath certificates"
	@$(VERUM) export --to coq      --with-provenance
	@$(VERUM) export --to lean     --with-provenance
	@$(VERUM) export --to dedukti  --with-provenance
	@$(VERUM) export --to metamath --with-provenance
	@echo "  ✔ all 4 formats emitted (agda dropped with CLI support)"

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------
.PHONY: clean
clean:
	@rm -rf target/ .verum_cache/ .z3-trace
	@find . -name "*.vbc" -delete
	@echo "▶ cleaned"

# Export inspection is an explicit hygiene gate, not mathematical certification.
.PHONY: certification-inventory certification-hygiene
certification-inventory:
	@$(PYTHON) scripts/certification_inventory.py --output certification-inventory.json
certification-hygiene:
	@$(PYTHON) scripts/certification_inventory.py --require-clean-exports
