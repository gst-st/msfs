import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MSFS_DIR = ROOT / "src/theorems/msfs"

EXPECTED_WAVE3_THEOREMS = {
    "wave3_certificate_adequacy": [
        "wave3_tariff_semilattice_and_diag_pb_obstruction",
        "wave3_adeq2cat_conical_noncancellation_and_w2",
        "wave3_cm_adeq_1_to_4_independence",
        "wave3_letbind_dag_vs_tree_actcost_gap",
        "wave3_php_exact_crossovers",
    ],
    "wave3_left_null_ips": [
        "wave3_general_left_null_refutation",
        "wave3_parametric_bezout_variety_elimination",
        "wave3_ordered_tuple_cofactor_left_null",
        "wave3_ordered_tuple_cramer_and_sign",
        "wave3_pivoted_bareiss_zero_leading_minor",
        "wave3_degree1_ips_alggate_bounds",
        "wave3_rabinowitsch_parametric_ips_no_inversion",
    ],
}

EXPECTED_CVE_CLOSURE_E = {
    "wave3_certificate_adequacy": 'cve_closure_E: "tests/test_wave3_certificate_adequacy.py"',
    "wave3_left_null_ips": 'cve_closure_E: "tests/test_wave3_proofs.py"',
}


def _strip_line_comments(text: str) -> str:
    return re.sub(r"//[^\n]*", "", text)


class Wave3ProofsTests(unittest.TestCase):
    def test_wave3_modules_and_theorems_mounted_in_mod(self):
        wave3_files = sorted(MSFS_DIR.glob("wave3_*.vr"))
        self.assertEqual(
            sorted(p.stem for p in wave3_files),
            sorted(EXPECTED_WAVE3_THEOREMS.keys()),
        )
        self.assertEqual(len(wave3_files), 2)

        mod_text = _strip_line_comments((MSFS_DIR / "mod.vr").read_text(encoding="utf-8"))
        total_theorems = 0
        for p in wave3_files:
            code = _strip_line_comments(p.read_text(encoding="utf-8"))
            mod_match = re.search(r"^\s*module\s+([^;]+);", code, re.M)
            self.assertIsNotNone(mod_match, f"missing module declaration in {p.name}")
            self.assertEqual(mod_match.group(1), f"lib.theorems.msfs.{p.stem}")

            thms = re.findall(r"^\s*public\s+theorem\s+([A-Za-z0-9_]+)", code, re.M)
            self.assertEqual(thms, EXPECTED_WAVE3_THEOREMS[p.stem], f"theorem list mismatch in {p.name}")
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

        self.assertEqual(total_theorems, 12)

    def test_wave3_structural_zero_axioms_and_arch_metadata(self):
        for stem in EXPECTED_WAVE3_THEOREMS:
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
            self.assertIsNone(
                re.search(r"\bensures\s*\{\s*let\b", code, re.S),
                f"forbidden `ensures {{ let ... }}` in {path.name}",
            )

            arch_match = re.search(r"@arch_module\((.*?)\)\s*module\s+", code, re.S)
            self.assertIsNotNone(arch_match, f"missing @arch_module in {path.name}")
            arch_body = arch_match.group(1)
            self.assertIn("Foundation.ZfcTwoInacc", arch_body)
            self.assertIn('Lifecycle.Theorem("v0.3")', arch_body)
            self.assertIn('cve_closure_C: "self"', arch_body)
            self.assertIn("VerifyStrategy.Formal", arch_body)
            self.assertIn(EXPECTED_CVE_CLOSURE_E[stem], arch_body)

            proof_blocks = re.findall(r"proof\s*\{(.*?)\}\s*;", code, re.S)
            self.assertEqual(
                len(proof_blocks),
                len(EXPECTED_WAVE3_THEOREMS[stem]),
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

    def test_wave3_substantiveness_and_zero_physics_guards(self):
        # 1. Zero `: Bool` fields in any Wave 3 record/struct definition.
        for stem in EXPECTED_WAVE3_THEOREMS:
            raw = (MSFS_DIR / f"{stem}.vr").read_text(encoding="utf-8")
            code = _strip_line_comments(raw)
            structs = re.findall(r"type\s+([A-Za-z0-9_]+)\s+is\s*\{(.*?)\}\s*;", code, re.S)
            self.assertGreaterEqual(len(structs), 1, f"expected at least 1 record type in {stem}.vr")
            for rec_name, rec_body in structs:
                self.assertIsNone(
                    re.search(r":\s*Bool\b", rec_body),
                    f"forbidden `: Bool` field in {stem}.vr::{rec_name}",
                )

            # Pure metatheory / algebra guard: zero physics terms in MSFS Wave 3 modules.
            lower = raw.lower()
            for forbidden in ("regge", "schwarzschild", "stelle", "pauli-villars", "pauli_villars", "kahler", "kähler", "cosmological"):
                self.assertIsNone(
                    re.search(rf"\b{re.escape(forbidden)}\b", lower),
                    f"forbidden physics term `{forbidden}` in {stem}.vr",
                )

        # 2. Axis 4 certificate adequacy & complexity witnesses.
        a4 = _strip_line_comments((MSFS_DIR / "wave3_certificate_adequacy.vr").read_text(encoding="utf-8"))
        for sym in (
            "TariffCoord",
            "is_valid_t12_coord",
            "AdeqTransFin",
            "total_drift",
            "signed_shift",
            "has_adeq_2cell",
            "Fin4AdeqModel",
            "is_cm1",
            "is_cm2",
            "is_cm3",
            "is_cm4",
            "BudgetedEnv",
            "act_cost_grade",
            "PhpCrossoverWitness",
        ):
            self.assertIn(sym, a4)

        # 3. Axis 2 §1 pure Left-Null / Bareiss / IPS witnesses.
        a2 = _strip_line_comments((MSFS_DIR / "wave3_left_null_ips.vr").read_text(encoding="utf-8"))
        for sym in (
            "LinSys2x1",
            "is_left_null_2x1",
            "ParamSpec",
            "bezout_combo",
            "Bordered3x2",
            "det_b1_ordered",
            "det_b1_sorted",
            "cramer_c0",
            "cramer_c1",
            "SwapBordered3x3",
            "b2_num",
            "b2_quot",
            "bareiss_signed_det",
            "AlgGateCircuitPlan",
            "direct_lin_ips_gates",
            "sparse_lin_ips_gates",
            "ns_to_ips_gates",
            "RabinowitschEval",
            "c_param_2x1",
        ):
            self.assertIn(sym, a2)

    def test_wave3_live_proof_honesty_audit_all_multi_step(self):
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
        self.assertGreaterEqual(report["by_lineage"]["msfs"]["theorem_multi_step"], 83)
        self.assertGreaterEqual(report["totals"]["theorem_multi_step"], 86)

        expected_rows = {
            thm: f"src/theorems/msfs/{stem}.vr"
            for stem, thms in EXPECTED_WAVE3_THEOREMS.items()
            for thm in thms
        }
        wave3_rows = {
            row["name"]: row
            for row in report["rows"]
            if row["file"].startswith("src/theorems/msfs/wave3_")
        }
        self.assertEqual(set(wave3_rows.keys()), set(expected_rows.keys()))
        for thm_name, expected_file in expected_rows.items():
            row = wave3_rows[thm_name]
            self.assertEqual(row["file"], expected_file)
            self.assertEqual(row["kind"], "theorem-multi-step", f"{thm_name} not theorem-multi-step")
            self.assertEqual(row["let_bindings"], 0, f"{thm_name} has let_bindings != 0")
            self.assertGreaterEqual(row["proof_body_steps"], 2, f"{thm_name} has < 2 proof_body_steps")


if __name__ == "__main__":
    unittest.main()
