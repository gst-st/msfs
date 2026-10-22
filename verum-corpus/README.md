# MSFS Verum corpus

Source formalization and verification work for *The Moduli Space of Formal Systems: Classification, Stabilization, and a No-Go Theorem for Absolute Foundations*, Max Sereda. The mathematical source is [the English paper](../paper-en/paper.tex); its verification ledger distinguishes proved mathematical statements from machine-checked artifacts.

The corpus is not yet a complete, independently replayable formalization of the paper. Successful parsing, type checking, framework coverage and compiler audit counters establish different properties. None alone certifies every theorem or a reduction of all assumptions to ZFC with two strongly inaccessible cardinals.

## Certification evidence

Run the reproducible inventory from this directory:

```sh
python3 scripts/certification_inventory.py --output certification-inventory.json
python3 -m unittest discover -s tests -p 'test_certification_inventory.py'
```

The inventory binds each inspected source and export to its SHA-256 and records the exact lines of recognized scaffolds. It grants no proof authority. The committed [inventory](certification-inventory.json) contains 28 Lean `sorry` definitions and 28 Coq `Admitted` commands; both exports also declare 43 opaque propositions. A declaration `axiom name : Prop` names an arbitrary proposition; it does not encode the mathematical statement or prove it. The Metamath export contains unknown proof bodies. The honesty baseline permits up to 43 placeholder axioms. Those are unresolved obligations, not evidence that only the advertised set-theoretic assumptions remain.

```sh
python3 scripts/certification_inventory.py --require-clean-exports
```

This hygiene gate currently fails on the retained scaffolds. A future successful hygiene check will still require independent logical replay and a faithful source-to-statement elaboration. Existing exports are retained as evidence and migration input; they must not be published as complete proof certificates.

## Verification contracts

For each theorem, certification needs:

1. The exact formal statement, including all binders, universes, hypotheses and foundation imports, linked to a fixed source revision.
2. A proof term checked against that statement by an identified Verum kernel, with every admitted assumption explicit.
3. Evidence that source elaboration preserves the statement. A label, hash, intrinsic dispatch name or successful check of a different statement is insufficient.
4. For an exported proof, preservation of its statement and assumptions and independent replay by the destination checker without `sorry`, `Admitted` or unknown proofs.

Verum's native judgment profile can replay closed terms with dependent functions, dependent pairs and identity elimination. It does not automatically elaborate all MSFS source contracts, categorical infrastructure or framework annotations. Noesis may retain the source, its formalization and the replay report as distinct objects; it must not promote a prose theorem based on a certificate attached by name.

## Checked source lemma and exact correspondence

The representation-level inclusion in `lem:SS-membership` now has two actual
Verum source proofs: [explicit presentation](proofs/ss-membership/witness.vr)
and [encoded formal witness](proofs/ss-membership/formal.vr). Neither assumes
membership of the target union. Both introduce its syntactic branch. The full
mathematical scope, universe levels and excluded categorical identifications
are stated in the [correspondence review](proofs/ss-membership/correspondence.txt).
The paper's statement has not been altered to fit these proofs.

```sh
python3 scripts/verify_source_membership.py \
  --checker /absolute/path/to/verum-source-replay \
  --noesis /absolute/path/to/noesis \
  --report proofs/ss-membership/replay-report.json
```

This command requires real executables. It checks the exact source/review hashes,
elaborates each form at three universe levels, and compares the entire native
statement and proof with an independently constructed named-term oracle. It then
stores the exact paper bytes, quoted source ports, correspondence review and proof
sources in a disposable Noesis database. Noesis repeats native verification;
mutated proofs must fail, historical proofs must remain valid, and archive restore
must preserve the exact results. It does not modify the deployed corpus.

[Recorded execution](proofs/ss-membership/replay-report.json): six exact
source/oracle comparisons, two ill-typed source mutations rejected, two source
proofs replayed before and after Noesis archive restoration, and two Noesis proof
mutations rejected. A Source edge verifies provenance, not the semantic adequacy
of a formalization. That distinction remains explicit in every report.

This closes the stated representation-inclusion proof. It does **not** replace
the legacy `core.math.s_definable` marker axiom or prove AFNT-alpha: the legacy
signature additionally promises global membership and mixes subtheory
interpretation with object identity. Those obligations remain separate. See the
[open mathematical and library defects](proofs/open-obligations.txt).

## Existing tooling

```sh
make check                # source check with the configured Verum build
make verify               # verification strategies supported by that build
make audit-honesty-gate   # existing source-shape regression gate
make audit-msfs           # framework and implementation audits
make export               # refuses proof exports until exact typed translation is available
```

Use a freshly built Verum and its matching `core` sources. Record the compiler revision, options, actual outputs and remaining assumptions. Source-shape gates and coverage summaries remain useful regression checks; they are not proof certification. The tutorial and historical audit outputs describe tooling workflows, not current blanket verification guarantees.

## Layout

- `src/theorems/msfs/`: source declarations and proof obligations.
- `tests/`: source-shape checks, integration scripts and certification inventory controls.
- `certificates/`: retained foreign exports and provenance metadata.
- `scripts/certification_inventory.py`: reproducible inspection without a solver or trusted certificate claim.
- `Makefile`: source check, verification, audit and export entry points.

The paper and formal source remain distinct until a faithful elaborator and independently checked correspondence close the gap. Replacing a difficult statement by an axiom, opaque proposition or trivial identity is not an acceptable completion strategy.
