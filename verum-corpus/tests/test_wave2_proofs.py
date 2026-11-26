import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MSFS_DIR = ROOT / "src/theorems/msfs"

EXPECTED_WAVE2_THEOREMS = {
    "wave2_b1_stabilization": [
        "wave2_b1_adjoint_triple_separation",
        "wave2_b1_tau0_breaks_rezk_completeness",
        "wave2_b1_unbounded_depth_separation",
        "wave2_b1_metric_exchange_law",
    ],
    "wave2_meta_stabilization": [
        "wave2_b2_fin_meta2_gauge_equivalence",
        "wave2_b2_exp_tower_and_pigeonhole_separation",
        "wave2_b2_m2_base_id_obstruction",
        "wave2_b2_m3_r_reflector_closure_laws",
        "wave2_b2_m3_r_reflector_join_failure",
        "wave2_b2_idem_joint_realizable",
        "wave2_b2_idem_clauses_independent",
    ],
    "wave2_meta_fib_categoricity": [
        "wave2_thm_meta_cat_fib_local_equiv",
        "wave2_fib_independence_countermodels",
    ],
    "wave2_dual_actica_2cat_core": [
        "wave2_actica_six_positive_implications",
        "wave2_actica_shift2cat_all_13",
        "wave2_actica_seven_countermodels",
    ],
    "wave2_subcanonical_sheaf_barrier": [
        "wave2_subcanonical_preserves_cofinal_nonrep",
        "wave2_coarse_topology_collapses_to_terminal",
    ],
    "wave2_ac_oc_2cat_perf": [
        "wave2_cm1_bf3_ore_failure",
        "wave2_cm2_bf4_cancellation_failure",
        "wave2_cm3_r2_phi_iota1_refutation",
        "wave2_perf2_ez2_gluing_and_bc",
        "wave2_cm4_capped_2cat_obstruction",
        "wave2_oac5_definitional_conservativity",
    ],
    "wave2_intensional_i_fragment": [
        "wave2_i_fragment_w2_separation",
        "wave2_i_fragment_w1_canonical_inclusion",
        "wave2_t233_strict_vs_isocomma",
        "wave2_i4a_diamond_no_right_adjoint",
        "wave2_i4a_f_bang_breaks_pullback",
        "wave2_i4a_strict_pb_bc_failure",
    ],
    "wave2_q2_completeness": [
        "wave2_q2_candidates_plural_nonmax",
        "wave2_q2_casm_realizer_obstruction",
        "wave2_q2_diagonal_escape_4",
        "wave2_q2_relative_completeness_basis4",
    ],
    "wave2_q3_witnesses": [
        "wave2_q3_d3_strong_dialetheia_non_explosive",
        "wave2_q3_d3_no_proper_subalgebra",
        "wave2_q3_bz2_lawvere_counterexample",
        "wave2_q3_precedence_partition_sound",
    ],
}


def _strip_line_comments(text: str) -> str:
    return re.sub(r"//[^\n]*", "", text)


class Wave2ProofsTests(unittest.TestCase):
    def test_wave2_modules_and_theorems_mounted_in_mod(self):
        wave2_files = sorted(MSFS_DIR.glob("wave2_*.vr"))
        self.assertEqual(
            sorted(p.stem for p in wave2_files),
            sorted(EXPECTED_WAVE2_THEOREMS.keys()),
        )
        self.assertEqual(len(wave2_files), 9)

        mod_text = _strip_line_comments((MSFS_DIR / "mod.vr").read_text(encoding="utf-8"))
        total_theorems = 0
        for p in wave2_files:
            code = _strip_line_comments(p.read_text(encoding="utf-8"))
            mod_match = re.search(r"^\s*module\s+([^;]+);", code, re.M)
            self.assertIsNotNone(mod_match, f"missing module declaration in {p.name}")
            self.assertEqual(mod_match.group(1), f"lib.theorems.msfs.{p.stem}")

            thms = re.findall(r"^\s*public\s+theorem\s+([A-Za-z0-9_]+)", code, re.M)
            self.assertEqual(thms, EXPECTED_WAVE2_THEOREMS[p.stem], f"theorem list mismatch in {p.name}")
            total_theorems += len(thms)

            mount_match = re.search(
                rf"mount\s+lib\.theorems\.msfs\.{re.escape(p.stem)}\.\{{(.*?)\}}\s*;",
                mod_text,
                re.S,
            )
            self.assertIsNotNone(mount_match, f"{p.stem} not mounted in mod.vr")
            mounted_items = [
                item.strip()
                for item in mount_match.group(1).split(",")
                if item.strip()
            ]
            self.assertEqual(
                mounted_items,
                thms,
                f"mounted theorem mismatch for {p.stem} in mod.vr",
            )

        self.assertEqual(total_theorems, 38)

    def test_wave2_structural_zero_axioms_and_arch_metadata(self):
        for stem in EXPECTED_WAVE2_THEOREMS:
            path = MSFS_DIR / f"{stem}.vr"
            code = _strip_line_comments(path.read_text(encoding="utf-8"))

            self.assertIsNone(
                re.search(r"^\s*(?:public\s+)?axiom\b", code, re.M),
                f"forbidden axiom in {path.name}",
            )
            self.assertIsNone(
                re.search(r"^\s*mount\b", code, re.M),
                f"forbidden mount import in {path.name}",
            )
            self.assertNotIn("core.math", code, f"forbidden core.math reference in {path.name}")
            self.assertIsNone(
                re.search(r"\bensures\s+true\b", code),
                f"forbidden `ensures true` in {path.name}",
            )

            arch_match = re.search(r"@arch_module\((.*?)\)\s*module\s+", code, re.S)
            self.assertIsNotNone(arch_match, f"missing @arch_module in {path.name}")
            arch_body = arch_match.group(1)
            self.assertIn("Foundation.ZfcTwoInacc", arch_body)
            self.assertIn('Lifecycle.Theorem("v0.2")', arch_body)
            self.assertIn('cve_closure_C: "self"', arch_body)
            self.assertIn("VerifyStrategy.Formal", arch_body)
            self.assertIn('cve_closure_E: "tests/test_wave2_proofs.py"', arch_body)

            proof_blocks = re.findall(r"proof\s*\{(.*?)\}\s*;", code, re.S)
            self.assertEqual(
                len(proof_blocks),
                len(EXPECTED_WAVE2_THEOREMS[stem]),
                f"proof block count mismatch in {path.name}",
            )
            for idx, pb in enumerate(proof_blocks):
                self.assertIsNone(
                    re.search(r"\b(let|obtain)\b", pb),
                    f"forbidden let/obtain in proof #{idx} of {path.name}",
                )
                steps = re.findall(r"\b(have|conclude)\b", pb)
                self.assertGreaterEqual(
                    len(steps),
                    2,
                    f"proof #{idx} in {path.name} has < 2 proof steps",
                )

    def test_wave2_substantiveness_guards(self):
        # 1. Zero `: Bool` fields in any Wave 2 record/struct definition.
        for stem in EXPECTED_WAVE2_THEOREMS:
            code = _strip_line_comments((MSFS_DIR / f"{stem}.vr").read_text(encoding="utf-8"))
            structs = re.findall(r"type\s+([A-Za-z0-9_]+)\s+is\s*\{(.*?)\}\s*;", code, re.S)
            self.assertGreaterEqual(len(structs), 1, f"expected at least 1 record type in {stem}.vr")
            for rec_name, rec_body in structs:
                self.assertIsNone(
                    re.search(r":\s*Bool\b", rec_body),
                    f"forbidden `: Bool` field in {stem}.vr::{rec_name}",
                )

        # 2. B1: FiniteAdj2CatSig must compute tau0_* via pure fns, not pre-baked fields.
        b1 = _strip_line_comments((MSFS_DIR / "wave2_b1_stabilization.vr").read_text(encoding="utf-8"))
        fin_adj = re.search(r"public type FiniteAdj2CatSig is \{(.*?)\};", b1, re.S).group(1)
        self.assertNotIn("tau0_", fin_adj)
        for sym in ("tau0_star_ob_eq_classes", "abs_diff", "delta2", "tilde_delta2"):
            self.assertIn(sym, b1)

        # 3. B2: Meta stabilization uses genuine finite tables, bitmask reflector, and 4 independence witnesses.
        b2 = _strip_line_comments((MSFS_DIR / "wave2_meta_stabilization.vr").read_text(encoding="utf-8"))
        for sym in ("FinMeta2", "MetaGaugeEquiv2", "fm16_inj", "r_reflector", "FiniteSiteModel3", "is_toy_idem_valid", "is_idem_not1", "is_idem_not2", "is_idem_not3", "is_idem_not4"):
            self.assertIn(sym, b2)

        # 4. B3: Fib categoricity, Dual Actica 13-axiom core, and subcanonical sheaf barrier.
        b3_fib = _strip_line_comments((MSFS_DIR / "wave2_meta_fib_categoricity.vr").read_text(encoding="utf-8"))
        for sym in ("Fib2CatSig", "is_two_obj_indisc_to_one", "is_no_fib1", "is_no_fib2_lift", "is_no_fib2_conn", "is_no_fib3_full", "is_no_fib3_faith"):
            self.assertIn(sym, b3_fib)

        b3_act = _strip_line_comments((MSFS_DIR / "wave2_dual_actica_2cat_core.vr").read_text(encoding="utf-8"))
        for sym in ("ActicaFiniteSig", "is_act_shift2cat_z2", "is_cm_not_a1", "is_cm_not_a6", "is_cm_not_a7", "is_cm_not_a8", "is_cm_not_a9", "is_cm_not_t_eps", "is_cm_not_t2a_star_star", "is_cm_not_t_eps_hom", "sat_all_13_act"):
            self.assertIn(sym, b3_act)

        b3_shf = _strip_line_comments((MSFS_DIR / "wave2_subcanonical_sheaf_barrier.vr").read_text(encoding="utf-8"))
        for sym in ("FiniteRankedSite3", "is_sheaf_3", "is_subcanonical", "is_sheafification_of"):
            self.assertIn(sym, b3_shf)

        # 5. B4: AC/OC 2-categorical perfection and countermodels.
        b4 = _strip_line_comments((MSFS_DIR / "wave2_ac_oc_2cat_perf.vr").read_text(encoding="utf-8"))
        for sym in ("CM1Table", "CM2Table", "Perf2EZ2Table", "Capped2Env", "DefConservFin", "is_enact_vcomp", "is_z2_vcomp"):
            self.assertIn(sym, b4)

        # 6. B5 & B6: Intensional I, Q2 completeness, and Q3 witnesses.
        b5 = _strip_line_comments((MSFS_DIR / "wave2_intensional_i_fragment.vr").read_text(encoding="utf-8"))
        for sym in ("Display2CatFin4", "FunctorMap4", "IsoCat2"):
            self.assertIn(sym, b5)

        q2 = _strip_line_comments((MSFS_DIR / "wave2_q2_completeness.vr").read_text(encoding="utf-8"))
        for sym in ("PartialClassifier6", "BinaryMatrix4", "InvariantQuotient4"):
            self.assertIn(sym, q2)

        q3 = _strip_line_comments((MSFS_DIR / "wave2_q3_witnesses.vr").read_text(encoding="utf-8"))
        for sym in ("Subalg3", "Q3Profile", "lp_sharp"):
            self.assertIn(sym, q3)

    def test_wave2_live_proof_honesty_audit_all_multi_step(self):
        verum_bin = shutil.which("verum")
        self.assertIsNotNone(verum_bin, "verum CLI binary must be available on PATH")

        env = {k: v for k, v in os.environ.items() if k != "VERUM_STDLIB_PATH"}
        proc = subprocess.run(
            [verum_bin, "audit", "--proof-honesty", "--format", "json"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        report = json.loads(proc.stdout)

        self.assertEqual(report["totals"]["axiom_placeholder"], 43)
        self.assertEqual(report["totals"]["theorem_no_proof_body"], 0)
        self.assertEqual(report["totals"]["theorem_trivial_true"], 0)
        self.assertEqual(report["by_lineage"]["msfs"]["axiom_placeholder"], 43)
        self.assertEqual(report["by_lineage"]["msfs"]["theorem_axiom_only"], 20)
        self.assertGreaterEqual(report["by_lineage"]["msfs"]["theorem_multi_step"], 71)
        self.assertGreaterEqual(report["totals"]["theorem_multi_step"], 74)

        expected_rows = {
            thm: f"src/theorems/msfs/{stem}.vr"
            for stem, thms in EXPECTED_WAVE2_THEOREMS.items()
            for thm in thms
        }
        wave2_rows = {
            row["name"]: row
            for row in report["rows"]
            if row["file"].startswith("src/theorems/msfs/wave2_")
        }
        self.assertEqual(set(wave2_rows.keys()), set(expected_rows.keys()))
        for thm_name, expected_file in expected_rows.items():
            row = wave2_rows[thm_name]
            self.assertEqual(row["file"], expected_file)
            self.assertEqual(row["kind"], "theorem-multi-step", f"{thm_name} not theorem-multi-step")
            self.assertEqual(row["let_bindings"], 0, f"{thm_name} has let_bindings != 0")
            self.assertGreaterEqual(row["proof_body_steps"], 2, f"{thm_name} has < 2 proof_body_steps")


if __name__ == "__main__":
    unittest.main()
