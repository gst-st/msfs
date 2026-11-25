import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "verify_wave1_proofs",
    ROOT / "scripts/verify_wave1_proofs.py",
)
verify_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_mod)


class Wave1ProofsTests(unittest.TestCase):
    def test_track_b_pi_id_oracle_and_negative_controls(self):
        results, neg_count = verify_mod.verify_track_b_oracles(ROOT)
        self.assertEqual(len(results), 9)
        self.assertGreaterEqual(neg_count, 16)
        self.assertTrue(all(r["status"] == "verified" and r["ast_1to1_match"] for r in results))

    def test_track_b_vr_direct_parsing_and_mutation_rejection(self):
        for rel_path, builder in verify_mod.TRACK_B_FILES:
            src = (ROOT / rel_path).read_text(encoding="utf-8")
            parsed = verify_mod.parse_and_compile_vr_text(src, level=0)
            ref = builder(0)
            self.assertEqual(parsed["name"], ref["name"])
            self.assertEqual(parsed["claimed_type"], ref["claimed_type"])
            self.assertEqual(parsed["term"], ref["term"])
            verify_mod.expect_universe((), parsed["claimed_type"])
            verify_mod.check((), parsed["term"], parsed["claimed_type"])

        alpha_src = (ROOT / "proofs/afnt-alpha-id/alpha_zero.vr").read_text(encoding="utf-8")
        mut_alpha = alpha_src.replace("exact(naive_pi4(x, hx, id_x));", "exact(x);")
        parsed_mut_alpha = verify_mod.parse_and_compile_vr_text(mut_alpha, level=0)
        with self.assertRaises(verify_mod.TypeCheckError):
            verify_mod.check((), parsed_mut_alpha["term"], parsed_mut_alpha["claimed_type"])

        lawvere_src = (ROOT / "proofs/afnt-alpha-id/lawvere_fp.vr").read_text(encoding="utf-8")
        mut_lawvere = lawvere_src.replace(
            "proof by rewrite(h_assoc1); induction h_diag_pt; rewrite(h_assoc2); rewrite < h_surj; reflexivity;",
            "proof by reflexivity;",
        )
        parsed_mut_law = verify_mod.parse_and_compile_vr_text(mut_lawvere, level=0)
        with self.assertRaises(verify_mod.TypeCheckError):
            verify_mod.check((), parsed_mut_law["term"], parsed_mut_law["claimed_type"])

        mut_rw = lawvere_src.replace("rewrite(h_assoc1);", "rewrite < h_assoc1;")
        with self.assertRaises(verify_mod.TypeCheckError):
            verify_mod.parse_and_compile_vr_text(mut_rw, level=0)

    def test_track_b_kernel_soundness_regressions(self):
        V = verify_mod.V
        U = verify_mod.U
        Lam = verify_mod.Lam
        Id = verify_mod.Id
        IdElim = verify_mod.IdElim
        J = verify_mod.J
        chain = verify_mod.chain
        compile_named = verify_mod.compile_named

        for bad_lvl in (-1, True, False):
            with self.assertRaises(verify_mod.TypeCheckError):
                verify_mod.check((), ("Universe", bad_lvl), ("Universe", 0))

        base_params = [
            ("A", U(0)),
            ("Bot", U(0)),
            ("a", V("A")),
            ("b", V("A")),
            ("scrut", Id(V("A"), V("a"), V("b"))),
        ]
        for dom2, base_term in [
            (U(0), Lam("_z", U(0), U(0))),
            (V("Bot"), Lam("_z", V("Bot"), V("Bot"))),
            (Id(V("A"), V("b"), V("y")), Lam("_z", Id(V("A"), V("b"), V("a")), Id(V("A"), V("b"), V("a")))),
        ]:
            tm = compile_named(chain(Lam, base_params, IdElim(Lam("y", V("A"), Lam("_p", dom2, U(0))), base_term, V("scrut"))))
            with self.assertRaises(verify_mod.TypeCheckError):
                verify_mod.infer((), tm)

        tm_j = compile_named(chain(Lam, base_params, J(Lam("y", V("A"), V("a")), V("a"), V("scrut"))))
        with self.assertRaises(verify_mod.TypeCheckError):
            verify_mod.infer((), tm_j)

    def test_track_b_correspondence_hashes_and_fragments(self):
        corr = verify_mod.verify_correspondence(ROOT, strict_paper_sha=False)
        self.assertEqual(
            set(corr["fragments_verified"]),
            {"thm:afnt-alpha", "thm:dual-afnt"},
        )
        self.assertEqual(
            corr["formalizations_verified"],
            [
                "afnt_alpha_zero_id_refutation",
                "lawvere_diagonal_fixed_point",
                "dual_afnt_route1a_retraction_refutation",
            ],
        )

    def test_track_a_wave1_structural_zero_axioms(self):
        track_a = verify_mod.verify_track_a_structural(ROOT)
        self.assertEqual(track_a["modules"], 4)
        self.assertEqual(track_a["total_theorems"], 17)

    def test_track_a_substantiveness_guards(self):
        diak = (ROOT / "src/theorems/msfs/wave1_diakrisis_2cat_core.vr").read_text()
        sig_block = re.search(r"public type DiakrisisFiniteSig is \{(.*?)\};", diak, re.S).group(1)
        self.assertNotIn(": Bool", sig_block)
        self.assertNotIn("rho_coeff == 0", diak)
        self.assertIn("sat_axi5(c6)", diak)
        self.assertIn("sat_axi7(c6)", diak)

        dual = (ROOT / "src/theorems/msfs/wave1_dual_enactment_core.vr").read_text()
        self.assertNotIn("PronkBFWitness", dual)
        ef3_block = re.search(r"public type EnactFin3 is \{(.*?)\};", dual, re.S).group(1)
        self.assertNotIn(": Bool", ef3_block)

    def test_open_obligations_consistency(self):
        obligations = (ROOT / "proofs/open-obligations.txt").read_text()
        for expected in (
            "wave1_meta_independence.vr",
            "wave1_grading_separation.vr",
            "wave1_dual_enactment_core.vr",
            "wave1_diakrisis_2cat_core.vr",
            "proofs/afnt-alpha-id/",
            "(alpha_diag)",
            "B1",
            "B6",
            "O4",
            "O6",
            "43",
        ):
            self.assertIn(expected, obligations)

    def test_proof_honesty_baseline_invariants(self):
        baseline = json.loads((ROOT / "tests/proof_honesty_baseline.json").read_text())
        self.assertGreaterEqual(baseline["totals_min"]["theorem_multi_step"], 36)
        self.assertEqual(baseline["totals_max"]["theorem_no_proof_body"], 0)
        self.assertEqual(baseline["totals_max"]["theorem_trivial_true"], 0)
        self.assertLessEqual(baseline["totals_max"]["axiom_placeholder"], 43)
        msfs_min = baseline["by_lineage_min"]["msfs"]
        msfs_max = baseline["by_lineage_max"]["msfs"]
        self.assertGreaterEqual(msfs_min["theorem_multi_step"], 33)
        self.assertEqual(msfs_min["theorem_axiom_only"], 20)
        self.assertLessEqual(msfs_max["axiom_placeholder"], 43)
        self.assertEqual(msfs_max["theorem_no_proof_body"], 0)
        self.assertEqual(msfs_max["theorem_trivial_true"], 0)

    def test_audit_report_synchronized(self):
        report = json.loads((ROOT / "audit-reports/proof-honesty.json").read_text())
        self.assertIn("_quarantine_note", report)
        self.assertEqual(report["totals"]["axiom_placeholder"], 43)
        self.assertEqual(report["totals"]["theorem_no_proof_body"], 0)
        self.assertEqual(report["totals"]["theorem_trivial_true"], 0)
        self.assertGreaterEqual(report["totals"]["theorem_multi_step"], 36)
        self.assertGreaterEqual(report["by_lineage"]["msfs"]["theorem_multi_step"], 33)
        self.assertEqual(report["by_lineage"]["msfs"]["theorem_axiom_only"], 20)

    def test_gitignore_ignores_verum_cache(self):
        gi = (ROOT / ".gitignore").read_text().splitlines()
        self.assertIn(".verum_cache/", gi)


if __name__ == "__main__":
    unittest.main()
