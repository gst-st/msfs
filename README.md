# MSFS — The Moduli Space of Formal Systems

*The Moduli Space of Formal Systems: Classification, Stabilization, and a No-Go Theorem for Absolute Foundations.*

Max Sereda, 2026 · [Zenodo DOI 10.5281/zenodo.19755781](https://doi.org/10.5281/zenodo.19755781) · 41 pages as initially deposited (`paper-en/zenodo/`); current post-audit revision: **`paper-en/msfs-paper.pdf` (39 pages, 1640 LaTeX lines)** and **`paper-ru/msfs-paper-ru.pdf` (42 pages, 1494 LaTeX lines, 1-to-1 Russian edition)** · **68 formal environments** (21 definitions, 7 lemmas, 17 theorems, 8 corollaries, 6 propositions, 7 remarks, 2 conventions) · companion [Verum corpus](./verum-corpus/) with portable kernel-checked source proofs and explicit assumption/obligation ledger.

## The question this work changes

Instead of asking *which formal system is the single true foundation of mathematics*, MSFS studies the categorical space of coherent foundations and its outer boundary:

> **What is the structure of the space of Rich foundations — which comparisons are unconditional, which require explicit lifting or localization data, and why is an absolute foundation impossible?**

The totality of formal foundations satisfying the Rich-metatheory conditions `(R1)–(R5)` is organized into a $2$-category $\mathcal{F}$ and (modulo Morita/gauge equivalence) a classifying $(\infty, 2)$-stack $\mathfrak{M}$. Following the **8 October 2026 Scope Audit** and subsequent **28 October 2026 Metatheoretic Audit (`O1–O3` resolved)**, the paper cleanly separates:
1. **Unconditional boundary results (`AFN-T α`, `AFN-T β`, `Dual-AFN-T`)**, proved in $\mathsf{ZFC} + 2\text{-inacc}$;
2. **Conditional interior comparison criteria** (`thm:meta-mult`, `thm:meta-cat`, `thm:slice-locality`, `thm:ac-oc-duality`, `thm:paraconsistent-afnt`), where exact lifting, descent, and translation hypotheses are stated explicitly;
3. **Open construction and stabilization obligations** (`thm:reflective`, `thm:meta-stab`, `cor:meta-closure`, `thm:bergner-lurie-stab`, `rem:grading-open`), recorded as explicit remarks rather than over-claimed as unconditionally closed theorems.

## Stratified architecture

```mermaid
flowchart LR
 classDef fnd fill:#bbdefb,stroke:#1976d2,color:#000
 classDef cls fill:#c8e6c9,stroke:#388e3c,color:#000
 classDef top fill:#fff9c4,stroke:#fbc02d,color:#000
 classDef abs fill:#ffccbc,stroke:#e64a19,color:#000,stroke-dasharray:5 5
 FND["𝓛_Fnd — Rich-foundations<br/>(R1)–(R5)"]:::fnd
 CLS["𝓛_Cls — classifiers<br/>(M1)–(M5)"]:::cls
 TOP["𝓛_Cls^⊤ — maximal<br/>(Max-1)–(Max-4)"]:::top
 ABS["𝓛_Abs = ∅<br/>(F_S) ∧ (Π_4) ∧ (Π_3-max)"]:::abs
 FND -- "Cls (horizontal meta)" --> CLS
 CLS -- "⊇ maximal subclass" --> TOP
 TOP -- "Gen (vertical meta)" --> ABS
```

| Stratum | Conditions | Status in current revision |
|---|---|---|
| $\mathcal{L}_{\mathrm{Fnd}}$ | `(R1)–(R5)` | Populated by $\mathsf{ZFC}$, $\mathsf{PA}$, $\mathsf{MLTT}$, $\mathsf{CIC}$, $\mathsf{HoTT}$, $\mathrm{Eff}$-theory, etc. |
| $\mathcal{L}_{\mathrm{Cls}}$ | `(M1)–(M5)` | Conditional plurality criterion (`thm:meta-mult`) for distinct essential classification images |
| $\mathcal{L}_{\mathrm{Cls}}^{\top}$ | `(Max-1)–(Max-4)` | Conditional biequivalence criterion (`thm:meta-cat`) given common comparison target & hom-equivalences |
| $\mathcal{L}_{\mathrm{Abs}}$ | $(F_S) \wedge (\Pi_{4, S, n}) \wedge (\Pi_{3\text{-max}, S, n})$ | **Unconditionally empty (`AFN-T`, `thm:afnt-alpha`)** |

## Summary of principal results

1. **Two-mechanism `AFN-T α` (`thm:afnt-alpha`, resolving `O1`).** Empty $\mathcal{L}_{\mathrm{Abs}}$ is established by two complementary mechanisms:
   - **Direct / slice-conservative mechanism $(\alpha_0)$**: when $F = S$ or $\mathrm{Syn}(\iota_F)$ is slice-conservative on $[\phi_X]$, Lemma `lem:SS-membership` places $X$ in $\mathcal{S}_S^{\mathrm{local}} \subseteq \mathcal{S}_S$, refuting $(F_S) \wedge (\Pi_{4,S,n})$ via the identity equivalence.
   - **Strong Diagonal Anti-Absoluteness $(\alpha_{\mathrm{diag}})$**: for *arbitrary* faithful subtheory inclusions $\iota_F : F \hookrightarrow S$ (without slice-conservativity and even if $\Pi_4$ is punctured or omitted), $(F_S) \wedge (\Pi_{3\text{-max},S,n})$ is refuted by testing against $T_S := \mathsf{PA} + \mathrm{Con}(S) \in \mathcal{F}$ (whose `(R3)` model is standard $\mathbb{N} \in \mathbf{U}_1 \subset \mathbf{U}_2$ via `(R3)` for $S$, without $\omega$-consistency), pulling back to a consistent r.e. extension $S_{\mathrm{arith}} \supseteq \mathsf{Q} + \mathrm{Con}(S)$, restricting to a Solovay $\mathsf{I\Delta_0} + \Omega_1$ cut, and applying Feferman–Pudlák Second Incompleteness (Feferman 1960; Pudlák 1985).
2. **Transfinite & proper-class `AFN-T β` (`thm:afnt-beta`, `prop:proper-class`, resolving `O2`).** $\mathbf{U}_2$-cofinal towers stay inside $\mathcal{S}_S^{\mathrm{global}}$, while arbitrary directed or proper-class towers obey an unconditional colimit $\mathrm{R\text{-}S}$-definability dichotomy on $A_\infty$ (illustrated by the terminal-collapse counterexample showing why diagram uniformity cannot be inferred from colimit definability).
3. **Two-stage `AC/OC` architecture (`sec:ac-oc-duality`, `thm:ac-oc-duality`, `thm:dual-afnt`).**
   - **Stage 1 (pre-localization)**: the section–forgetful adjunction $\varepsilon \dashv \alpha : \mathcal{E} \to \mathcal{F}$ is strictly asymmetric ($\alpha \circ \varepsilon = \mathrm{id}_{\mathcal{F}}$, whereas each enactment fiber $\alpha^{-1}(F)$ retains non-isomorphic semantic realizations and operational resource budgets).
   - **Stage 2 (post-localization)**: under explicit localization, descent, and coherence hypotheses, inverting reflection morphisms $\mathcal{R}_{\mathcal{E}}$ yields a coarse equivalence $\mathfrak{M} \simeq \mathfrak{M}_{\mathcal{E}}$. Independently of localization, $\mathcal{L}_{\mathrm{Abs}}^{\mathcal{E}} = \emptyset$ holds unconditionally (`thm:dual-afnt`).
4. **Verified ordinary display slice & grade-zero collapse (`thm:I-existence`, `prop:grading`, `cor:grade-collapse`).** Ordinary slice display categories form a verified contravariant pseudofunctor, while equivalence-seeded display filtrations collapse at grade zero; non-trivial higher intensional refinements (`(I-1)–(I-4)`, citing Kapulkin–Li 2025) are stated as explicit construction obligations.
5. **Paraconsistent conditional transfer (`def:paraconsistent-rs`, `thm:paraconsistent-afnt`, resolving `O3`).** Formulated with existential non-explosion ($\exists \phi,\, \bot \not\vdash_{S'} \phi$) and explicit predicate-preserving classical-kernel translation hypotheses.

## Verification & companion formalizations

- **Portable Verum source proof (`verum-corpus/proofs/ss-membership/`)**: machine-checked representation-level introduction proof (`witness.vr`, `formal.vr`), bound byte-for-byte to `paper-en/paper.tex` (`conv:notation`, `def:SS`, `lem:SS-membership`) via `correspondence.json` and audited by `verum-corpus/scripts/certification_inventory.py` and `verify_source_membership.py`. Legacy framework/marker files in `verum-corpus/src/` are inventoried honestly as non-discharging scaffolds (`verum-corpus/proofs/open-obligations.txt`, Appendix `app:verification-ledger`).
- **Lean 4 kernel formalization (sibling `math-foundations/lean4-mf-kernel/`)**: zero-`sorry`, zero-axiom, choice-free (`0` `Classical.choice`) constructive formalizations of Strong Diagonal `AFN-T α` (`MathFoundations/Metatheory/StrongAFNT.lean`) and the asymmetric pre-localization adjunction vs coarse localization (`MathFoundations/Metatheory/ReifActAdjunction.lean`).

## Build

```bash
# English edition → paper-en/msfs-paper.pdf
bun scripts/build-paper.ts

# Russian 1-to-1 edition → paper-ru/msfs-paper-ru.pdf
bun scripts/build-paper.ts --paper msfs-ru

# Inventory & correspondence unit tests
python3 verum-corpus/scripts/certification_inventory.py --output verum-corpus/certification-inventory.json
python3 -m unittest discover -s verum-corpus/tests -p 'test_*.py'
```

## Relationship to Diakrisis and Math Foundations

| Programme / Gateway | MSFS Labels |
|---|---|
| `AFN-T α` & `AFN-T β` | `lem:SS-membership`, `thm:afnt-alpha`, `thm:afnt-beta`, `prop:proper-class` (§4–§6) |
| Five-axis analysis | `thm:horizontal`, `thm:vertical`, `thm:meta-vertical`, `thm:lateral`, `thm:completeness` (§7) |
| Display slice & grading | `thm:I-existence`, `thm:slice-locality`, `prop:grading`, `cor:grade-collapse`, `rem:grading-open` (§8) |
| Classifier comparison & open stabilization | `thm:meta-cat`, `thm:meta-mult`, `thm:meta-stab`, `cor:iteration-closure`, `cor:meta-closure` (§9) |
| Two-stage `AC/OC` & `Dual-AFN-T` | `def:enactments`, `thm:ac-oc-duality`, `cor:ac-oc-conservativity`, `thm:dual-afnt` (§10) |

## Licence

- **Paper content** (`paper-en/`, `paper-ru/`): CC BY 4.0 (`LICENSE`).
- **Build & audit scripts** (`scripts/`, `verum-corpus/scripts/`): MIT (`LICENSE` §B).
