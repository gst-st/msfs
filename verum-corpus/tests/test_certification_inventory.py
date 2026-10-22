import importlib.util
import tempfile
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("inventory",Path(__file__).resolve().parents[1]/"scripts/certification_inventory.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class InventoryTests(unittest.TestCase):
    def test_export_markers_are_evidence_not_proofs(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/"certificates").mkdir()
            path=root/"certificates/theorem.lean"
            path.write_text("axiom named_claim : Prop\ndef claimed_theorem : Prop := sorry\n")
            report=module.inventory(root)
            self.assertEqual({f["kind"] for f in report["exports"][0]["findings"]},{"sorry","opaque_proposition"})
            old=report["exports"][0]["sha256"]
            path.write_text("-- all proven, certified=true\n")
            changed=module.inventory(root)
            self.assertNotEqual(changed["exports"][0]["sha256"],old)
            self.assertEqual(changed["exports"][0]["findings"],[])
            self.assertEqual(changed["source_elaboration"],"not_certified")
            self.assertEqual(changed["exports"][0]["logical_replay"],"not_performed")
    def test_no_files_cannot_mean_every_theorem_verified(self):
        with tempfile.TemporaryDirectory() as name:
            self.assertEqual(module.inventory(name)["authority"],"inventory_only")
if __name__=="__main__": unittest.main()
