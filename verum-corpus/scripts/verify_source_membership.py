#!/usr/bin/env python3
"""Replay the exact source lemma through Verum and an isolated Noesis store.

Requires real executables. No mock kernels, inferred proof authority, or production
knowledge-store writes. Failure never refreshes expected source identities.
"""
import argparse
import base64
import hashlib
import json
import re
import subprocess
import tempfile
import uuid
from pathlib import Path
from membership_oracle import certificate

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "verum-source-pi-id/1"
MEDIA = "application/vnd.verum.source+json"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def replay(checker, request):
    run = subprocess.run([str(checker), "--worker"], input=json.dumps(request),
                         text=True, capture_output=True, timeout=30, check=True)
    return json.loads(run.stdout)

def load_review(root=ROOT):
    manifest = json.loads((root / "proofs/ss-membership/correspondence.json").read_text())
    paper = (root.parent / manifest["source"]["path"]).read_bytes()
    require(sha(paper) == manifest["source"]["sha256"], "The reviewed paper changed; a new correspondence review is required")
    require(sha((root / manifest["review"]).read_bytes()) == manifest["review_sha256"], "Correspondence review changed")
    for fragment in manifest["source"]["fragments"]:
        data = paper[fragment["start"]:fragment["end"]]
        require(data.decode() == fragment["quote"] and sha(data) == fragment["sha256"], "Source quotation mismatch")
    for item in manifest["formalizations"]:
        require(sha((root / item["path"]).read_bytes()) == item["sha256"], "Formal source changed; review required")
    return manifest, paper

def noesis_cycle(binary, checker, manifest, paper, requests):
    with tempfile.TemporaryDirectory(prefix="msfs-noesis-") as tmp:
        directory = Path(tmp)
        def cli(store, *args):
            command = [str(binary), "--db", str(directory / store / "state.sqlite"),
                       "--token-file", str(directory / store / "owner.token"),
                       "--verum-source-checker", str(checker), *args]
            result = subprocess.run(command, text=True, capture_output=True, timeout=45, check=True)
            return json.loads(result.stdout)
        def call(operation, store="original"):
            path = directory / "request.json"
            path.write_text(json.dumps({"protocol":"noesis/1", "request_id":str(uuid.uuid4()), "operation":operation}))
            return cli(store, "call", "--request", str(path))
        cli("original", "init")
        call({"type":"create_corpus", "corpus":"msfs", "title":"MSFS source correspondence", "domain":"mathematics"})
        def put(object_name, data, media="text/plain", dependencies=(), kind="source"):
            head = call({"type":"snapshot", "corpus":"msfs", "snapshot":None})["digest"]
            op = {"type":"put", "corpus":"msfs", "expected_head":head, "object":object_name,
                  "kind":kind, "media_type":media, "data":base64.b64encode(data).decode(), "dependencies":list(dependencies)}
            return call(op), op
        original, _ = put("paper-en/paper.tex", paper)
        dependencies = [{"role":f["anchor"], "relation":"source", "object":"paper-en/paper.tex",
                         "revision":original["revision"], "fragment":{k:f[k] for k in ("start","end","quote")}}
                        for f in manifest["source"]["fragments"]]
        review, _ = put(manifest["review"], (ROOT / manifest["review"]).read_bytes(), dependencies=dependencies, kind="note")
        queries = []
        for request in requests:
            stored, op = put("proofs/"+request["declaration"]+".json", json.dumps(request).encode(), MEDIA,
                             [*dependencies, {"role":"correspondence_review", "relation":"citation", "object":manifest["review"],
                               "revision":review["revision"], "fragment":None}], "support")
            query = {"type":"check_formal", "corpus":"msfs", "snapshot":stored["snapshot"],
                     "object":op["object"], "revision":stored["revision"]}
            checked = call(query)["formal"]
            require(checked["status"] == "verified", "Noesis independent source replay failed")
            require(checked["source_alignment"] == "not_checked", "Prose was incorrectly certified")
            require(checked["dependency_semantics"] == "not_used", "Citation silently became a premise")
            require(checked["elaboration"]["report"]["source"]["sha256"] == sha(request["source"].encode()), "Wrong source checked")
            # A changed proof is a new object: neither its label nor its Source edge grants authority.
            broken = dict(request, source=request["source"].split("proof =")[0]+"proof = x;")
            bad, _ = put(op["object"], json.dumps(broken).encode(), MEDIA, op["dependencies"], "support")
            rejected = call(dict(query, snapshot=bad["snapshot"], revision=bad["revision"]))["formal"]
            require(rejected["status"] == "rejected", "A proof mutation retained verification authority")
            require(call(query)["formal"] == checked, "Historical verified revision changed")
            queries.append((query, checked))
        archive = directory / "archive.json"
        cli("original", "export", "--corpus", "msfs", "--format", "archive", "--output", str(archive))
        cli("restored", "init")
        cli("restored", "restore", "--archive", str(archive))
        for query, before in queries:
            require(call(query, "restored")["formal"] == before, "Restored source proof or provenance changed")
        return {"source_sha256":sha(paper), "original_and_restored_proofs":len(queries),
                "proof_mutations_rejected":len(queries), "reports":[checked for _,checked in queries]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checker", required=True, type=Path)
    parser.add_argument("--noesis", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    checker, noesis = args.checker.resolve(strict=True), args.noesis.resolve(strict=True)
    manifest, paper = load_review()
    report = {"profile":"msfs-source-replay/1", "checker_binary_sha256":sha(checker.read_bytes()),
              "noesis_binary_sha256":sha(noesis.read_bytes()), "source_elaborations":[], "negative_controls":[],
              "prose_alignment":"reviewed_representation_inclusion_only", "not_covered":manifest["not_covered"]}
    requests = []
    for item in manifest["formalizations"]:
        source = (ROOT / item["path"]).read_text()
        request = {"profile":PROFILE, "source":source, "declaration":item["declaration"]}
        requests.append(request)
        for level in (0, 1, 2):
            variant = dict(request, source=re.sub(r"\bType\b", f"Type({level})", source) if level else source)
            actual = replay(checker, variant)
            expected = certificate(level, "witness" in item["declaration"])
            require(actual["status"] == "verified" and actual["native"]["accepted"], "Native proof failed")
            require(actual["source"]["sha256"] == sha(variant["source"].encode()), "Wrong source identity")
            span = actual["source"]["span"]
            require(sha(variant["source"].encode()[span["start"]:span["end"]]) == span["sha256"], "Wrong declaration span")
            judgment = actual["judgment"]
            require(judgment["statement"] == expected["claimed_type"], "Elaboration changed the independently specified theorem")
            for key in ("term", "claimed_type"):
                require(judgment["certificate"][key] == expected[key], "Elaboration/oracle mismatch: "+key)
            report["source_elaborations"].append({"declaration":item["declaration"], "universe":level,
                "source":actual["source"], "elaborator":actual["elaborator"], "native":actual["native"],
                "exact_independent_oracle":True})
        broken = dict(request, source=source.split("proof =")[0]+"proof = x;")
        rejected = replay(checker, broken)
        require(rejected["status"] == "rejected" and rejected["diagnostic"]["code"] == "ill_typed_source", "Bad proof did not reach typed rejection")
        report["negative_controls"].append({"declaration":item["declaration"], "mutation":"same statement; replace proof with object x", "status":rejected["status"], "code":rejected["diagnostic"]["code"]})
    report["noesis"] = noesis_cycle(noesis, checker, manifest, paper, requests)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print("6 exact source/oracle comparisons; 2 source mutations rejected; 2 Noesis source proofs replayed before/after archive, 2 Noesis mutations rejected.")

if __name__ == "__main__":
    main()
