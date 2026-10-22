#!/usr/bin/env python3
"""Reproducible evidence inventory. This scanner grants no proof authority."""
import argparse
import hashlib
import json
import re
from pathlib import Path

PATTERNS = {
    ".lean": {"sorry": r"^def\s+\S+\s*:\s*Prop\s*:=\s*sorry\b", "opaque_proposition": r"^axiom\s+\S+\s*:\s*Prop\b"},
    ".v": {"admitted": r"^Admitted\.", "opaque_proposition": r"^Axiom\s+\S+\s*:\s*Prop\b"},
    ".dk": {"admitted_marker": r"admitted|scaffold"},
    ".mm": {"unknown_proof": r"\$=\s*\?\s*\$\.", "syntax_axiom": r"\$a\s+wff\b"},
}

def inventory(root):
    root=Path(root)
    sources=[]
    for path in sorted((root/"src").rglob("*.vr")):
        data=path.read_bytes()
        sources.append({"path":str(path.relative_to(root)),"sha256":hashlib.sha256(data).hexdigest()})
    exports=[]
    for path in sorted((root/"certificates").rglob("*")):
        if not path.is_file() or path.suffix not in PATTERNS: continue
        data=path.read_bytes(); findings=[]
        for number,line in enumerate(data.decode("utf-8").splitlines(),1):
            for kind,pattern in PATTERNS[path.suffix].items():
                if re.search(pattern,line): findings.append({"line":number,"kind":kind,"text":line})
        exports.append({"path":str(path.relative_to(root)),"sha256":hashlib.sha256(data).hexdigest(),"findings":findings,"logical_replay":"not_performed"})
    baseline_path=root/"tests/proof_honesty_baseline.json"
    baseline=json.loads(baseline_path.read_text()) if baseline_path.exists() else {}
    return {"profile":"msfs-certification-inventory/1","authority":"inventory_only",
        "source_elaboration":"not_certified","sources":sources,"exports":exports,
        "baseline_axiom_placeholder_ceiling":baseline.get("totals_max",{}).get("axiom_placeholder"),
        "limits":["Lexical inspection is not a proof checker; an absent marker does not establish a valid proof.",
            "A name declared at Prop is not the mathematical statement represented by that name.",
            "Native proof replay must be linked to a faithful elaboration of each source statement; a file hash or an annotation is insufficient."]}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output",type=Path)
    parser.add_argument("--require-clean-exports",action="store_true",help="Fail on recognized scaffold markers or missing exports; success is only hygiene, never certification.")
    args=parser.parse_args(); report=inventory(args.root)
    text=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
    if args.output: args.output.write_text(text)
    else: print(text,end="")
    if args.require_clean_exports and (not report["exports"] or any(e["findings"] for e in report["exports"])): raise SystemExit(1)
