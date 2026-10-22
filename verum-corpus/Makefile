# =============================================================================
# verum-corpus Makefile — MSFS machine-verification CI / build / audit shortcuts
# =============================================================================
#
# Single entry point for every operation a reviewer or maintainer might
# perform on this corpus.  Run `make help` for the full target list.
#
#   • `make`                   — source check and source-shape regression gates (not proof certification)
#   • `make check`             — type-check the corpus
#   • `make verify`            — run the verification ladder
#   • `make audit`             — emit every audit report into audit-reports/
#   • `make audit-msfs`        — MSFS-specific audits (htt, ar, self-recognition)
#   • `make export`            — request exact foreign proofs (unsupported until typed translation exists)
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
	@echo "  make / make default            source-shape checks (not proof certification)"
	@echo "  make check                     verum check (type-check)"
	@echo "  make verify                    verum verify (full ladder)"
	@echo "  make smoke                     run smoke test suite"
	@echo "  make export                    request exact foreign proofs (unsupported until typed translation exists)"
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
	@echo "▶ requesting proof export; unsupported typed translation must fail explicitly"
	@$(VERUM) export --to lean --with-provenance

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

# Exact-source proof plus independent oracle and Noesis archive replay.
# Paths must identify the actual freshly built executables.
.PHONY: certify-source
certify-source:
	@test -n "$(VERUM_SOURCE_CHECKER)" -a -n "$(NOESIS)" || (echo "Set VERUM_SOURCE_CHECKER and NOESIS to built executables" >&2; exit 1)
	@$(PYTHON) scripts/verify_source_membership.py --checker "$(VERUM_SOURCE_CHECKER)" --noesis "$(NOESIS)" --report proofs/ss-membership/replay-report.json
