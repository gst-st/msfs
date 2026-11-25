#!/usr/bin/env python3
"""Independent .vr parser, named-AST / de Bruijn Pi/Id kernel, and Wave 1 verifier.

Verification boundary (honest reporting):
  - Verifies SHA-256 digests of Track B artifacts (`proofs/afnt-alpha-id/`),
    correspondence review, and quoted `paper-en/paper.tex` fragments (including
    exact byte-offset slices).
  - Parses and compiles `proofs/afnt-alpha-id/{alpha_zero.vr, lawvere_fp.vr,
    route1a_retraction.vr}` directly from `.vr` source text into named ASTs
    and de Bruijn terms, verifies 1-to-1 AST equivalence with the reference
    certificates, and type-checks the compiled `.vr` proof terms in an
    independent Python bidirectional Martin-Lof Pi + Id + J + IdElim kernel at
    universe levels 0, 1, 2 (plus kernel & `.vr`-mutation negative controls).
  - Verifies Track A (`src/theorems/msfs/wave1_*.vr`) structural invariants
    (zero axioms, zero `core.math.*` imports, zero `ensures true`).
  - Does NOT claim `verum-source-replay` or `noesis` ran when those binaries
    are absent from PATH; reports their availability explicitly.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# =============================================================================
# 1. Independent Named-AST -> de Bruijn Compiler & Bidirectional Pi/Id Kernel
# =============================================================================

def V(name): return ("var", name)
def U(level): return ("universe", level)
def Pi(name, domain, codomain): return ("pi", name, domain, codomain)
def Lam(name, domain, body): return ("lam", name, domain, body)
def App(fn, arg): return ("app", fn, arg)
def Id(carrier, lhs, rhs): return ("id", carrier, lhs, rhs)
def Refl(val): return ("refl", val)
def J(motive, base, scrutinee): return ("j", motive, base, scrutinee)
def IdElim(motive, base, scrutinee): return ("id_elim", motive, base, scrutinee)


class TypeCheckError(Exception):
    pass


class VrParseError(Exception):
    pass


def validate_universe_level(level):
    if not isinstance(level, int) or isinstance(level, bool) or level < 0:
        raise TypeCheckError(f"invalid universe level {level!r}: expected int >= 0")
    return level


def chain(kind, binders, body):
    for name, domain in reversed(binders):
        body = kind(name, domain, body)
    return body


def compile_named(term, scope=()):
    kind = term[0]
    if kind == "var":
        name = term[1]
        if name not in scope:
            raise ValueError(f"unbound variable {name!r} in scope {scope}")
        return ("Var", scope[::-1].index(name))
    if kind == "universe":
        lvl = validate_universe_level(term[1])
        return ("Universe", lvl)
    if kind in ("pi", "lam"):
        _, name, domain, body = term
        tag = "Pi" if kind == "pi" else "Lam"
        return (tag, compile_named(domain, scope), compile_named(body, (*scope, name)))
    if kind == "app":
        return ("App", compile_named(term[1], scope), compile_named(term[2], scope))
    if kind == "id":
        return ("Id", compile_named(term[1], scope), compile_named(term[2], scope), compile_named(term[3], scope))
    if kind == "refl":
        return ("Refl", compile_named(term[1], scope))
    if kind == "j":
        return ("J", compile_named(term[1], scope), compile_named(term[2], scope), compile_named(term[3], scope))
    if kind == "id_elim":
        return ("IdElim", compile_named(term[1], scope), compile_named(term[2], scope), compile_named(term[3], scope))
    raise ValueError(f"unknown AST node {kind!r}")


def shift(term, amount, cutoff=0):
    k = term[0]
    if k == "Var":
        idx = term[1]
        return ("Var", idx + amount if idx >= cutoff else idx)
    if k == "Universe":
        return term
    if k in ("Pi", "Lam"):
        return (k, shift(term[1], amount, cutoff), shift(term[2], amount, cutoff + 1))
    if k == "App":
        return ("App", shift(term[1], amount, cutoff), shift(term[2], amount, cutoff))
    if k == "Id":
        return ("Id", shift(term[1], amount, cutoff), shift(term[2], amount, cutoff), shift(term[3], amount, cutoff))
    if k == "Refl":
        return ("Refl", shift(term[1], amount, cutoff))
    if k in ("J", "IdElim"):
        return (k, shift(term[1], amount, cutoff), shift(term[2], amount, cutoff), shift(term[3], amount, cutoff))
    raise TypeCheckError(f"bad term {k}")


def subst(term, target, value):
    k = term[0]
    if k == "Var":
        idx = term[1]
        if idx == target:
            return value
        if idx > target:
            return ("Var", idx - 1)
        return term
    if k == "Universe":
        return term
    if k in ("Pi", "Lam"):
        return (k, subst(term[1], target, value), subst(term[2], target + 1, shift(value, 1, 0)))
    if k == "App":
        return ("App", subst(term[1], target, value), subst(term[2], target, value))
    if k == "Id":
        return ("Id", subst(term[1], target, value), subst(term[2], target, value), subst(term[3], target, value))
    if k == "Refl":
        return ("Refl", subst(term[1], target, value))
    if k in ("J", "IdElim"):
        return (k, subst(term[1], target, value), subst(term[2], target, value), subst(term[3], target, value))
    raise TypeCheckError(f"bad term {k}")


def whnf(term):
    while True:
        k = term[0]
        if k == "App":
            fn = whnf(term[1])
            if fn[0] == "Lam":
                term = subst(fn[2], 0, term[2])
                continue
            return ("App", fn, term[2])
        if k == "J":
            scrut = whnf(term[3])
            if scrut[0] == "Refl":
                term = term[2]
                continue
            return ("J", term[1], term[2], scrut)
        if k == "IdElim":
            scrut = whnf(term[3])
            if scrut[0] == "Refl":
                term = term[2]
                continue
            return ("IdElim", term[1], term[2], scrut)
        return term


def conv(t1, t2):
    t1 = whnf(t1)
    t2 = whnf(t2)
    if t1[0] != t2[0]:
        return False
    k = t1[0]
    if k in ("Var", "Universe"):
        return t1[1] == t2[1]
    if k in ("Pi", "Lam"):
        # Eta-free structural conversion after WHNF; sufficient for closed proofs
        return conv(t1[1], t2[1]) and conv(t1[2], t2[2])
    if k == "App":
        return conv(t1[1], t2[1]) and conv(t1[2], t2[2])
    if k == "Id":
        return conv(t1[1], t2[1]) and conv(t1[2], t2[2]) and conv(t1[3], t2[3])
    if k == "Refl":
        return conv(t1[1], t2[1])
    if k in ("J", "IdElim"):
        return conv(t1[1], t2[1]) and conv(t1[2], t2[2]) and conv(t1[3], t2[3])
    return False


def expect_universe(ctx, ty):
    w = whnf(infer(ctx, ty))
    if w[0] != "Universe":
        raise TypeCheckError(f"expected Universe for type {ty}, got {w}")
    return validate_universe_level(w[1])


def infer(ctx, term):
    k = term[0]
    if k == "Var":
        idx = term[1]
        if not isinstance(idx, int) or isinstance(idx, bool) or idx < 0 or idx >= len(ctx):
            raise TypeCheckError(f"de Bruijn index {idx} out of context (len={len(ctx)})")
        return shift(ctx[-(idx + 1)], idx + 1, 0)
    if k == "Universe":
        lvl = validate_universe_level(term[1])
        return ("Universe", lvl + 1)
    if k == "Pi":
        u_dom = expect_universe(ctx, term[1])
        u_cod = expect_universe((*ctx, term[1]), term[2])
        return ("Universe", max(u_dom, u_cod))
    if k == "Lam":
        expect_universe(ctx, term[1])
        body_ty = infer((*ctx, term[1]), term[2])
        return ("Pi", term[1], body_ty)
    if k == "App":
        fn_ty = whnf(infer(ctx, term[1]))
        if fn_ty[0] != "Pi":
            raise TypeCheckError(f"application of non-function type {fn_ty}")
        check(ctx, term[2], fn_ty[1])
        return subst(fn_ty[2], 0, term[2])
    if k == "Id":
        u = expect_universe(ctx, term[1])
        check(ctx, term[2], term[1])
        check(ctx, term[3], term[1])
        return ("Universe", u)
    if k == "Refl":
        val_ty = infer(ctx, term[1])
        return ("Id", val_ty, term[1], term[1])
    if k == "J":
        # Endpoint-only transport matching scoped.rs / proof_checker.rs:
        # motive : (x : A) -> Type u, scrutinee : Id(A, a, b), base : motive(a) => motive(b)
        motive, base, scrut = term[1], term[2], term[3]
        scrut_ty = whnf(infer(ctx, scrut))
        if scrut_ty[0] != "Id":
            raise TypeCheckError(f"J scrutinee must be Id, got {scrut_ty}")
        carrier, lhs, rhs = scrut_ty[1], scrut_ty[2], scrut_ty[3]
        motive_ty = whnf(infer(ctx, motive))
        if motive_ty[0] != "Pi" or not conv(motive_ty[1], carrier):
            raise TypeCheckError(f"J motive domain mismatch: {motive_ty} vs {carrier}")
        expect_universe((*ctx, carrier), motive_ty[2])
        if whnf(motive_ty[2])[0] != "Universe":
            raise TypeCheckError(f"J motive codomain must be a Universe, got {motive_ty[2]}")
        # motive(lhs) must be well-typed and base : motive(lhs)
        check(ctx, base, ("App", motive, lhs))
        return ("App", motive, rhs)
    if k == "IdElim":
        # Full path induction: motive : (y : A) -> Id(A, a, y) -> Type u
        motive, base, scrut = term[1], term[2], term[3]
        scrut_ty = whnf(infer(ctx, scrut))
        if scrut_ty[0] != "Id":
            raise TypeCheckError(f"IdElim scrutinee must be Id, got {scrut_ty}")
        carrier, lhs, rhs = scrut_ty[1], scrut_ty[2], scrut_ty[3]
        motive_ty = whnf(infer(ctx, motive))
        if motive_ty[0] != "Pi" or not conv(motive_ty[1], carrier):
            raise TypeCheckError(f"IdElim motive domain mismatch: {motive_ty}")
        inner_pi = whnf(motive_ty[2])
        if inner_pi[0] != "Pi":
            raise TypeCheckError("IdElim motive must take endpoint and path")
        expected_path_dom = ("Id", shift(carrier, 1, 0), shift(lhs, 1, 0), ("Var", 0))
        if not conv(inner_pi[1], expected_path_dom):
            raise TypeCheckError(f"IdElim motive path domain mismatch: {inner_pi[1]} vs {expected_path_dom}")
        expect_universe((*ctx, carrier, inner_pi[1]), inner_pi[2])
        if whnf(inner_pi[2])[0] != "Universe":
            raise TypeCheckError(f"IdElim motive codomain must be a Universe, got {inner_pi[2]}")
        expected_base_ty = ("App", ("App", motive, lhs), ("Refl", lhs))
        check(ctx, base, expected_base_ty)
        return ("App", ("App", motive, rhs), scrut)
    raise TypeCheckError(f"unknown term {k}")


def check(ctx, term, expected):
    inferred = infer(ctx, term)
    if not conv(inferred, expected):
        raise TypeCheckError(f"type mismatch:\n  inferred: {inferred}\n  expected: {expected}")


# =============================================================================
# 2. Direct `.vr` Lexer, Parser, and Tactic-to-Pi/Id Compiler
# =============================================================================

_TOKEN_RE = re.compile(
    r"\s*(?:"
    r"//[^\n]*"
    r"|/\*.*?\*/"
    r"|(->|[()<>,.:;])"
    r"|([A-Za-z_][A-Za-z0-9_]*)"
    r")",
    re.S,
)


def tokenize_vr(text: str):
    tokens = []
    pos = 0
    n = len(text)
    while pos < n:
        if text[pos].isspace():
            pos += 1
            continue
        m = _TOKEN_RE.match(text, pos)
        if not m:
            snippet = text[pos:pos + 30]
            raise VrParseError(f"unexpected character near {snippet!r}")
        if m.group(1) is not None:
            tokens.append(("SYM", m.group(1)))
        elif m.group(2) is not None:
            tokens.append(("IDENT", m.group(2)))
        pos = m.end()
    tokens.append(("EOF", ""))
    return tokens


class VrParser:
    def __init__(self, tokens, level: int):
        self.tokens = tokens
        self.pos = 0
        self.level = validate_universe_level(level)
        self._anon_counter = 0

    def _fresh_anon(self) -> str:
        name = f"_anon_{self._anon_counter}"
        self._anon_counter += 1
        return name

    def peek(self):
        return self.tokens[self.pos]

    def match(self, kind, val=None):
        tk, tv = self.peek()
        if tk == kind and (val is None or tv == val):
            self.pos += 1
            return tv
        return None

    def expect(self, kind, val=None):
        res = self.match(kind, val)
        if res is None:
            raise VrParseError(f"expected ({kind}, {val}), got {self.peek()} at token {self.pos}")
        return res

    def parse_theorem(self):
        self.expect("IDENT", "public")
        self.expect("IDENT", "theorem")
        name = self.expect("IDENT")
        self.expect("SYM", "(")
        params = []
        if not self.match("SYM", ")"):
            while True:
                p_name = self.expect("IDENT")
                self.expect("SYM", ":")
                p_ty = self.parse_type_expr()
                params.append((p_name, p_ty))
                if self.match("SYM", ")"):
                    break
                self.expect("SYM", ",")
        self.expect("SYM", ":")
        ret_ty = self.parse_type_expr()
        self.expect("IDENT", "proof")
        self.expect("IDENT", "by")
        tactics = self.parse_tactic_seq()
        self.expect("EOF")
        return {
            "name": name,
            "params": params,
            "return_type": ret_ty,
            "tactics": tactics,
        }

    def parse_type_expr(self):
        tk, tv = self.peek()
        if tk == "IDENT" and tv == "Type":
            self.pos += 1
            return U(self.level)
        if tk == "IDENT" and tv == "forall":
            self.pos += 1
            self.expect("SYM", "(")
            b_name = self.expect("IDENT")
            self.expect("SYM", ":")
            b_ty = self.parse_type_expr()
            self.expect("SYM", ")")
            self.expect("SYM", ".")
            cod = self.parse_type_expr()
            return Pi(b_name, b_ty, cod)
        if tk == "IDENT" and tv == "fn":
            self.pos += 1
            binders = []
            if self.match("SYM", "<"):
                while True:
                    m_name = self.expect("IDENT")
                    self.expect("SYM", ":")
                    self.match("IDENT", "meta")
                    m_ty = self.parse_type_expr()
                    binders.append((m_name, m_ty))
                    if self.match("SYM", ">"):
                        break
                    self.expect("SYM", ",")
            self.expect("SYM", "(")
            if not self.match("SYM", ")"):
                while True:
                    a_ty = self.parse_type_expr()
                    binders.append((self._fresh_anon(), a_ty))
                    if self.match("SYM", ")"):
                        break
                    self.expect("SYM", ",")
            self.expect("SYM", "->")
            cod = self.parse_type_expr()
            return chain(Pi, binders, cod)
        if tk == "IDENT" and tv == "Path":
            self.pos += 1
            self.expect("SYM", "<")
            carrier = self.parse_type_expr()
            self.expect("SYM", ">")
            self.expect("SYM", "(")
            lhs = self.parse_term_expr()
            self.expect("SYM", ",")
            rhs = self.parse_term_expr()
            self.expect("SYM", ")")
            return Id(carrier, lhs, rhs)
        return self.parse_term_expr()

    def parse_term_expr(self):
        if self.match("SYM", "("):
            inner = self.parse_term_expr()
            self.expect("SYM", ")")
            return inner
        ident = self.expect("IDENT")
        expr = V(ident)
        if self.match("SYM", "("):
            if not self.match("SYM", ")"):
                while True:
                    arg = self.parse_term_expr()
                    expr = App(expr, arg)
                    if self.match("SYM", ")"):
                        break
                    self.expect("SYM", ",")
        return expr

    def parse_tactic_seq(self):
        tactics = []
        while self.peek()[0] != "EOF":
            tactics.append(self.parse_one_tactic())
            if not self.match("SYM", ";"):
                break
        return tactics

    def parse_one_tactic(self):
        kw = self.expect("IDENT")
        if kw == "intro":
            self.expect("SYM", "(")
            names = []
            while True:
                names.append(self.expect("IDENT"))
                if self.match("SYM", ")"):
                    break
                self.expect("SYM", ",")
            return ("intro", names)
        if kw == "exact":
            self.expect("SYM", "(")
            tm = self.parse_term_expr()
            self.expect("SYM", ")")
            return ("exact", tm)
        if kw == "rewrite":
            if self.match("SYM", "<"):
                h_name = self.expect("IDENT")
                return ("rewrite_bwd", h_name)
            if self.match("SYM", "("):
                h_name = self.expect("IDENT")
                self.expect("SYM", ")")
                return ("rewrite_fwd", h_name)
            h_name = self.expect("IDENT")
            return ("rewrite_fwd", h_name)
        if kw == "induction":
            h_name = self.expect("IDENT")
            return ("induction", h_name)
        if kw == "reflexivity":
            return ("reflexivity",)
        raise VrParseError(f"unknown tactic {kw!r}")


def rename_named(term, old_name: str, new_name: str):
    if old_name == new_name:
        return term
    k = term[0]
    if k == "var":
        return V(new_name) if term[1] == old_name else term
    if k == "universe":
        return term
    if k in ("pi", "lam"):
        _, b, dom, cod = term
        new_dom = rename_named(dom, old_name, new_name)
        if b == old_name:
            return (k, b, new_dom, cod)
        return (k, b, new_dom, rename_named(cod, old_name, new_name))
    if k == "app":
        return App(rename_named(term[1], old_name, new_name), rename_named(term[2], old_name, new_name))
    if k == "id":
        return Id(
            rename_named(term[1], old_name, new_name),
            rename_named(term[2], old_name, new_name),
            rename_named(term[3], old_name, new_name),
        )
    if k == "refl":
        return Refl(rename_named(term[1], old_name, new_name))
    if k in ("j", "id_elim"):
        return (
            k,
            rename_named(term[1], old_name, new_name),
            rename_named(term[2], old_name, new_name),
            rename_named(term[3], old_name, new_name),
        )
    raise VrParseError(f"unknown AST node {k!r}")


def free_vars_named(term):
    k = term[0]
    if k == "var":
        return {term[1]}
    if k == "universe":
        return set()
    if k in ("pi", "lam"):
        return free_vars_named(term[2]) | (free_vars_named(term[3]) - {term[1]})
    if k == "app":
        return free_vars_named(term[1]) | free_vars_named(term[2])
    if k == "id":
        return free_vars_named(term[1]) | free_vars_named(term[2]) | free_vars_named(term[3])
    if k == "refl":
        return free_vars_named(term[1])
    if k in ("j", "id_elim"):
        return free_vars_named(term[1]) | free_vars_named(term[2]) | free_vars_named(term[3])
    return set()


def replace_subterm_named(term, target, replacement):
    if term == target:
        return replacement, 1
    k = term[0]
    if k in ("var", "universe"):
        return term, 0
    if k in ("pi", "lam"):
        _, b, dom, cod = term
        new_dom, c1 = replace_subterm_named(dom, target, replacement)
        if b in free_vars_named(target) or b in free_vars_named(replacement):
            return (k, b, new_dom, cod), c1
        new_cod, c2 = replace_subterm_named(cod, target, replacement)
        return (k, b, new_dom, new_cod), c1 + c2
    if k == "app":
        a1, c1 = replace_subterm_named(term[1], target, replacement)
        a2, c2 = replace_subterm_named(term[2], target, replacement)
        return App(a1, a2), c1 + c2
    if k == "id":
        c_t, c0 = replace_subterm_named(term[1], target, replacement)
        l_t, c1 = replace_subterm_named(term[2], target, replacement)
        r_t, c2 = replace_subterm_named(term[3], target, replacement)
        return Id(c_t, l_t, r_t), c0 + c1 + c2
    if k == "refl":
        v_t, c0 = replace_subterm_named(term[1], target, replacement)
        return Refl(v_t), c0
    if k in ("j", "id_elim"):
        m_t, c0 = replace_subterm_named(term[1], target, replacement)
        b_t, c1 = replace_subterm_named(term[2], target, replacement)
        s_t, c2 = replace_subterm_named(term[3], target, replacement)
        return (k, m_t, b_t, s_t), c0 + c1 + c2
    return term, 0


class TacticCompiler:
    def __init__(self):
        self._fresh_id = 0

    def fresh(self, prefix="_z"):
        name = f"{prefix}{self._fresh_id}"
        self._fresh_id += 1
        return name

    def compile(self, env_list, goal, tactics):
        # env_list: list of (logical_name, actual_var_name, named_type)
        if not tactics:
            raise TypeCheckError(f"incomplete proof: unclosed goal {goal}")
        tac = tactics[0]
        rest = tactics[1:]
        tk = tac[0]

        if tk == "intro":
            names = tac[1]
            if not names:
                return self.compile(env_list, goal, rest)
            cur_goal = goal
            cur_env = list(env_list)
            binders = []
            for nm in names:
                if cur_goal[0] != "pi":
                    raise TypeCheckError(f"intro({nm}) requires Pi goal, got {cur_goal}")
                _, old_b, dom, cod = cur_goal
                cod_renamed = rename_named(cod, old_b, nm)
                binders.append((nm, dom))
                cur_env.append((nm, nm, dom))
                cur_goal = cod_renamed
            body = self.compile(cur_env, cur_goal, rest)
            return chain(Lam, binders, body)

        if tk == "exact":
            if rest:
                raise TypeCheckError("tactics remain after exact(...)")
            tm = tac[1]
            # Resolve any logical hypothesis aliases in `tm`
            for log_name, act_name, _ in env_list:
                if log_name != act_name:
                    tm = rename_named(tm, log_name, act_name)
            return tm

        if tk == "reflexivity":
            if rest:
                raise TypeCheckError("tactics remain after reflexivity")
            if goal[0] != "id":
                raise TypeCheckError(f"reflexivity requires Path/Id goal, got {goal}")
            return Refl(goal[2])

        if tk in ("rewrite_fwd", "rewrite_bwd"):
            h_name = tac[1]
            match = [e for e in env_list if e[0] == h_name]
            if not match:
                raise TypeCheckError(f"unknown hypothesis {h_name!r} in rewrite")
            _, act_h, h_ty = match[-1]
            if h_ty[0] != "id":
                raise TypeCheckError(f"rewrite hypothesis {h_name!r} is not Id: {h_ty}")
            carrier, lhs, rhs = h_ty[1], h_ty[2], h_ty[3]
            z_var = self.fresh("_z")
            if tk == "rewrite_fwd":
                motive_body, count = replace_subterm_named(goal, lhs, V(z_var))
                if count == 0:
                    raise TypeCheckError(f"rewrite({h_name}) LHS {lhs} not found in goal {goal}")
                new_goal, _ = replace_subterm_named(goal, lhs, rhs)
                subproof = self.compile(env_list, new_goal, rest)
                z_rev = self.fresh("_zrev")
                rev_proof = J(Lam(z_rev, carrier, Id(carrier, V(z_rev), lhs)), Refl(lhs), V(act_h))
                return J(Lam(z_var, carrier, motive_body), subproof, rev_proof)
            else:
                motive_body, count = replace_subterm_named(goal, rhs, V(z_var))
                if count == 0:
                    raise TypeCheckError(f"rewrite < {h_name} RHS {rhs} not found in goal {goal}")
                new_goal, _ = replace_subterm_named(goal, rhs, lhs)
                subproof = self.compile(env_list, new_goal, rest)
                return J(Lam(z_var, carrier, motive_body), subproof, V(act_h))

        if tk == "induction":
            h_name = tac[1]
            match = [(i, e) for i, e in enumerate(env_list) if e[0] == h_name]
            if not match:
                raise TypeCheckError(f"unknown hypothesis {h_name!r} in induction")
            h_idx, (_, act_h, h_ty) = match[-1]
            if h_ty[0] != "id":
                raise TypeCheckError(f"induction hypothesis {h_name!r} is not Id: {h_ty}")
            carrier, lhs, rhs = h_ty[1], h_ty[2], h_ty[3]
            ep = self.fresh("_ep")
            ev = self.fresh("_ev")

            # Generalize later hypotheses in env_list whose types contain `rhs`
            dep_hyps = []
            new_env = list(env_list)
            for idx in range(h_idx + 1, len(env_list)):
                l_name, a_name, ty = env_list[idx]
                ty_ep, cnt = replace_subterm_named(ty, rhs, V(ep))
                if cnt > 0:
                    g_name = self.fresh(f"_{l_name}_g")
                    ty_lhs, _ = replace_subterm_named(ty, rhs, lhs)
                    dep_hyps.append((l_name, a_name, g_name, ty_ep, ty_lhs))
                    new_env[idx] = (l_name, g_name, ty_lhs)

            goal_ep, _ = replace_subterm_named(goal, rhs, V(ep))
            goal_lhs, _ = replace_subterm_named(goal, rhs, lhs)

            motive_cod = chain(Pi, [(g_name, ty_ep) for _, _, g_name, ty_ep, _ in dep_hyps], goal_ep)
            motive = Lam(ep, carrier, Lam(ev, Id(carrier, lhs, V(ep)), motive_cod))

            subproof = self.compile(new_env, goal_lhs, rest)
            base = chain(Lam, [(g_name, ty_lhs) for _, _, g_name, _, ty_lhs in dep_hyps], subproof)

            tm = IdElim(motive, base, V(act_h))
            for _, a_name, _, _, _ in dep_hyps:
                tm = App(tm, V(a_name))
            return tm

        raise TypeCheckError(f"unsupported tactic {tk!r}")


def parse_and_compile_vr_text(source_text: str, level: int = 0):
    tokens = tokenize_vr(source_text)
    parsed = VrParser(tokens, level).parse_theorem()
    params = parsed["params"]
    ret_ty = parsed["return_type"]
    env_list = [(p_name, p_name, p_ty) for p_name, p_ty in params]
    body_named = TacticCompiler().compile(env_list, ret_ty, parsed["tactics"])
    claimed_named = chain(Pi, params, ret_ty)
    term_named = chain(Lam, params, body_named)
    return {
        "name": parsed["name"],
        "claimed_type": compile_named(claimed_named),
        "term": compile_named(term_named),
    }


def parse_and_compile_vr_file(path: Path, level: int = 0):
    return parse_and_compile_vr_text(path.read_text(encoding="utf-8"), level=level)


# =============================================================================
# 3. Reference Named-AST Certificates for Cross-Checking Parsed `.vr` ASTs
# =============================================================================

def cert_afnt_alpha_zero(level: int):
    params = [
        ("obj", U(level)),
        ("hom", Pi("_a", V("obj"), Pi("_b", V("obj"), U(level)))),
        ("p", Pi("_x", V("obj"), U(level))),
        ("x", V("obj")),
        ("id_x", App(App(V("hom"), V("x")), V("x"))),
        ("hx", App(V("p"), V("x"))),
        ("bot", U(level)),
        ("naive_pi4", Pi("y", V("obj"),
            Pi("_py", App(V("p"), V("y")),
               Pi("_h", App(App(V("hom"), V("x")), V("y")), V("bot"))))),
    ]
    body = App(App(App(V("naive_pi4"), V("x")), V("hx")), V("id_x"))
    return {
        "name": "afnt_alpha_zero_id_refutation",
        "claimed_type": compile_named(chain(Pi, params, V("bot"))),
        "term": compile_named(chain(Lam, params, body)),
    }


def cert_dual_afnt_route1a(level: int):
    params = [
        ("enact", U(level)),
        ("hom_e", Pi("_a", V("enact"), Pi("_b", V("enact"), U(level)))),
        ("ss_e", Pi("_e", V("enact"), U(level))),
        ("equiv_on_img", Pi("e1", V("enact"), Pi("e2", V("enact"),
            Pi("_m", App(App(V("hom_e"), V("e1")), V("e2")), U(level))))),
        ("e", V("enact")),
        ("in_sse", App(V("ss_e"), V("e"))),
        ("id_e", App(App(V("hom_e"), V("e")), V("e"))),
        ("id_equiv", App(App(App(V("equiv_on_img"), V("e")), V("e")), V("id_e"))),
        ("bot", U(level)),
        ("naive_pi4_tilde", Pi("e2", V("enact"),
            Pi("m", App(App(V("hom_e"), V("e")), V("e2")),
               Pi("_ss", App(V("ss_e"), V("e2")),
                  Pi("_eq", App(App(App(V("equiv_on_img"), V("e")), V("e2")), V("m")),
                     V("bot")))))),
    ]
    body = App(App(App(App(V("naive_pi4_tilde"), V("e")), V("id_e")), V("in_sse")), V("id_equiv"))
    return {
        "name": "dual_afnt_route1a_retraction_refutation",
        "claimed_type": compile_named(chain(Pi, params, V("bot"))),
        "term": compile_named(chain(Lam, params, body)),
    }


def cert_lawvere_fp(level: int):
    def c3(x, y, z, f, g):
        return App(App(App(App(App(V("comp"), x), y), z), f), g)

    def hty(x, y):
        return App(App(V("hom"), x), y)

    y0 = c3(V("t"), V("prod_aa"), V("y"), V("pair_aa"), V("eval_map"))
    rhs_assoc1 = c3(V("t"), V("prod_aa"), V("y"), V("pair_aa"),
                    c3(V("prod_aa"), V("y"), V("y"), V("eval_map"), V("f")))
    a0_diag = c3(V("t"), V("a"), V("prod_aa"), V("a0"), V("diag"))
    d_rhs = c3(V("t"), V("a"), V("y"), V("a0"),
               c3(V("a"), V("prod_aa"), V("y"), V("diag"),
                  c3(V("prod_aa"), V("y"), V("y"), V("eval_map"), V("f"))))

    params = [
        ("obj", U(level)),
        ("hom", Pi("_x", V("obj"), Pi("_y", V("obj"), U(level)))),
        ("comp", Pi("x", V("obj"), Pi("y", V("obj"), Pi("z", V("obj"),
            Pi("_f", hty(V("x"), V("y")),
               Pi("_g", hty(V("y"), V("z")), hty(V("x"), V("z")))))))),
        ("t", V("obj")),
        ("a", V("obj")),
        ("prod_aa", V("obj")),
        ("y", V("obj")),
        ("diag", hty(V("a"), V("prod_aa"))),
        ("eval_map", hty(V("prod_aa"), V("y"))),
        ("f", hty(V("y"), V("y"))),
        ("pair_aa", hty(V("t"), V("prod_aa"))),
        ("a0", hty(V("t"), V("a"))),
        ("h_assoc1", Id(hty(V("t"), V("y")), c3(V("t"), V("y"), V("y"), y0, V("f")), rhs_assoc1)),
        ("h_diag_pt", Id(hty(V("t"), V("prod_aa")), V("pair_aa"), a0_diag)),
        ("h_assoc2", Id(hty(V("t"), V("y")),
            c3(V("t"), V("prod_aa"), V("y"), a0_diag, c3(V("prod_aa"), V("y"), V("y"), V("eval_map"), V("f"))),
            d_rhs)),
        ("h_surj", Id(hty(V("t"), V("y")), y0, d_rhs)),
    ]

    goal = Id(hty(V("t"), V("y")), c3(V("t"), V("y"), V("y"), y0, V("f")), y0)

    def rev_path(carrier, lhs, rhs, path_term):
        return J(
            Lam("_z", carrier, Id(carrier, V("_z"), lhs)),
            Refl(lhs),
            path_term,
        )

    step4 = J(
        Lam("_z4", hty(V("t"), V("y")), Id(hty(V("t"), V("y")), V("_z4"), y0)),
        Refl(y0),
        V("h_surj"),
    )

    h_assoc2_gen = Id(
        hty(V("t"), V("y")),
        c3(V("t"), V("prod_aa"), V("y"), V("ep"),
           c3(V("prod_aa"), V("y"), V("y"), V("eval_map"), V("f"))),
        d_rhs,
    )
    step3_in_base = J(
        Lam("_z3", hty(V("t"), V("y")), Id(hty(V("t"), V("y")), V("_z3"), y0)),
        step4,
        rev_path(
            hty(V("t"), V("y")),
            c3(V("t"), V("prod_aa"), V("y"), V("pair_aa"),
               c3(V("prod_aa"), V("y"), V("y"), V("eval_map"), V("f"))),
            d_rhs,
            V("h_assoc2_g"),
        ),
    )

    motive_diag = Lam("ep", hty(V("t"), V("prod_aa")),
        Lam("_ev", Id(hty(V("t"), V("prod_aa")), V("pair_aa"), V("ep")),
            Pi("h_assoc2_g", h_assoc2_gen,
               Id(hty(V("t"), V("y")),
                  c3(V("t"), V("prod_aa"), V("y"), V("pair_aa"),
                     c3(V("prod_aa"), V("y"), V("y"), V("eval_map"), V("f"))),
                  y0))))
    base_diag = Lam("h_assoc2_g",
        Id(hty(V("t"), V("y")),
           c3(V("t"), V("prod_aa"), V("y"), V("pair_aa"),
              c3(V("prod_aa"), V("y"), V("y"), V("eval_map"), V("f"))),
           d_rhs),
        step3_in_base)
    step2 = App(IdElim(motive_diag, base_diag, V("h_diag_pt")), V("h_assoc2"))

    step1 = J(
        Lam("_z1", hty(V("t"), V("y")), Id(hty(V("t"), V("y")), V("_z1"), y0)),
        step2,
        rev_path(
            hty(V("t"), V("y")),
            c3(V("t"), V("y"), V("y"), y0, V("f")),
            rhs_assoc1,
            V("h_assoc1"),
        ),
    )

    return {
        "name": "lawvere_diagonal_fixed_point",
        "claimed_type": compile_named(chain(Pi, params, goal)),
        "term": compile_named(chain(Lam, params, step1)),
    }


TRACK_B_FILES = [
    ("proofs/afnt-alpha-id/alpha_zero.vr", cert_afnt_alpha_zero),
    ("proofs/afnt-alpha-id/lawvere_fp.vr", cert_lawvere_fp),
    ("proofs/afnt-alpha-id/route1a_retraction.vr", cert_dual_afnt_route1a),
]


def _expect_rejected(fn, exc_types, msg):
    try:
        fn()
    except exc_types:
        return
    raise AssertionError(msg)


def verify_track_b_oracles(root: Path = ROOT):
    results = []
    for rel_path, ref_builder in TRACK_B_FILES:
        vr_path = root / rel_path
        src_text = vr_path.read_text(encoding="utf-8")
        for lvl in (0, 1, 2):
            parsed_cert = parse_and_compile_vr_text(src_text, level=lvl)
            ref_cert = ref_builder(lvl)
            if parsed_cert["name"] != ref_cert["name"]:
                raise AssertionError(f"name mismatch for {rel_path}: {parsed_cert['name']} vs {ref_cert['name']}")
            if parsed_cert["claimed_type"] != ref_cert["claimed_type"]:
                raise AssertionError(f"claimed_type AST mismatch for {rel_path} at level {lvl}")
            if parsed_cert["term"] != ref_cert["term"]:
                raise AssertionError(f"proof term AST mismatch for {rel_path} at level {lvl}")
            expect_universe((), parsed_cert["claimed_type"])
            check((), parsed_cert["term"], parsed_cert["claimed_type"])
            results.append({
                "declaration": parsed_cert["name"],
                "path": rel_path,
                "universe": lvl,
                "ast_1to1_match": True,
                "status": "verified",
            })

    neg_count = 0

    # 1. Negative control: corrupted alpha_zero term (x instead of naive_pi4(...))
    bad_alpha = cert_afnt_alpha_zero(0)
    bad_alpha_term = compile_named(chain(Lam, [
        ("obj", U(0)),
        ("hom", Pi("_a", V("obj"), Pi("_b", V("obj"), U(0)))),
        ("p", Pi("_x", V("obj"), U(0))),
        ("x", V("obj")),
        ("id_x", App(App(V("hom"), V("x")), V("x"))),
        ("hx", App(V("p"), V("x"))),
        ("bot", U(0)),
        ("naive_pi4", Pi("y", V("obj"),
            Pi("_py", App(V("p"), V("y")),
               Pi("_h", App(App(V("hom"), V("x")), V("y")), V("bot"))))),
    ], V("x")))
    _expect_rejected(
        lambda: check((), bad_alpha_term, bad_alpha["claimed_type"]),
        TypeCheckError,
        "negative control bad_alpha unexpectedly accepted",
    )
    neg_count += 1

    # 2. Negative control: corrupted lawvere term (Refl(y0) for y0 >> f = y0)
    bad_lawvere = cert_lawvere_fp(0)
    bad_lawvere_term = ("Lam", bad_lawvere["term"][1], ("Refl", ("Var", 0)))
    _expect_rejected(
        lambda: check((), bad_lawvere_term, bad_lawvere["claimed_type"]),
        TypeCheckError,
        "negative control bad_lawvere unexpectedly accepted",
    )
    neg_count += 1

    # 3. Negative control: Universe(-1) and Universe(True) / Universe(False)
    for bad_lvl in (-1, -5, True, False, "0"):
        _expect_rejected(
            lambda l=bad_lvl: check((), ("Universe", l), ("Universe", 0)),
            TypeCheckError,
            f"negative control Universe({bad_lvl!r}) unexpectedly accepted",
        )
        neg_count += 1

    # 4. Negative controls: IdElim bogus 2nd domains (U(0), Bot, Id(A, b, y)) and bogus codomains
    idelim_base_params = [
        ("A", U(0)),
        ("Bot", U(0)),
        ("a", V("A")),
        ("b", V("A")),
        ("scrut", Id(V("A"), V("a"), V("b"))),
    ]
    for label, dom2, cod2, base_term in [
        ("U(0)", U(0), U(0), Lam("_z", U(0), U(0))),
        ("Bot", V("Bot"), U(0), Lam("_z", V("Bot"), V("Bot"))),
        ("Id(A,b,y)", Id(V("A"), V("b"), V("y")), U(0),
         Lam("_z", Id(V("A"), V("b"), V("a")), Id(V("A"), V("b"), V("a")))),
    ]:
        bad_motive = Lam("y", V("A"), Lam("_p", dom2, cod2))
        bad_idelim = compile_named(chain(Lam, idelim_base_params, IdElim(bad_motive, base_term, V("scrut"))))
        _expect_rejected(
            lambda t=bad_idelim: infer((), t),
            TypeCheckError,
            f"negative control IdElim bogus 2nd domain {label} unexpectedly accepted",
        )
        neg_count += 1

    # IdElim bogus non-universe codomain (returns term `a : A` instead of a type)
    bad_idelim_cod = compile_named(chain(Lam, idelim_base_params, IdElim(
        Lam("y", V("A"), Lam("_p", Id(V("A"), V("a"), V("y")), V("a"))),
        V("a"),
        V("scrut"),
    )))
    _expect_rejected(
        lambda: infer((), bad_idelim_cod),
        TypeCheckError,
        "negative control IdElim non-universe codomain unexpectedly accepted",
    )
    neg_count += 1

    # 5. Negative control: J bogus non-universe codomain (returns term `a : A` instead of a type)
    bad_j_cod = compile_named(chain(Lam, idelim_base_params, J(
        Lam("y", V("A"), V("a")),
        V("a"),
        V("scrut"),
    )))
    _expect_rejected(
        lambda: infer((), bad_j_cod),
        TypeCheckError,
        "negative control J non-universe codomain unexpectedly accepted",
    )
    neg_count += 1

    # 6. Negative controls: mutated `.vr` proof bodies (bypassing manifest SHA)
    alpha_src = (root / "proofs/afnt-alpha-id/alpha_zero.vr").read_text(encoding="utf-8")
    mut_alpha = alpha_src.replace("exact(naive_pi4(x, hx, id_x));", "exact(x);")
    assert mut_alpha != alpha_src
    _expect_rejected(
        lambda: check((), parse_and_compile_vr_text(mut_alpha, 0)["term"],
                      parse_and_compile_vr_text(mut_alpha, 0)["claimed_type"]),
        TypeCheckError,
        "negative control mutated alpha_zero.vr (exact(x)) unexpectedly accepted",
    )
    neg_count += 1

    lawvere_src = (root / "proofs/afnt-alpha-id/lawvere_fp.vr").read_text(encoding="utf-8")
    mut_lawvere_refl = lawvere_src.replace(
        "proof by rewrite(h_assoc1); induction h_diag_pt; rewrite(h_assoc2); rewrite < h_surj; reflexivity;",
        "proof by reflexivity;",
    )
    assert mut_lawvere_refl != lawvere_src
    _expect_rejected(
        lambda: check((), parse_and_compile_vr_text(mut_lawvere_refl, 0)["term"],
                      parse_and_compile_vr_text(mut_lawvere_refl, 0)["claimed_type"]),
        TypeCheckError,
        "negative control mutated lawvere_fp.vr (reflexivity) unexpectedly accepted",
    )
    neg_count += 1

    mut_lawvere_rw = lawvere_src.replace("rewrite(h_assoc1);", "rewrite < h_assoc1;")
    assert mut_lawvere_rw != lawvere_src
    _expect_rejected(
        lambda: parse_and_compile_vr_text(mut_lawvere_rw, 0),
        TypeCheckError,
        "negative control mutated lawvere_fp.vr (wrong rewrite direction) unexpectedly accepted",
    )
    neg_count += 1

    mut_lawvere_rw2 = lawvere_src.replace("rewrite(h_assoc1);", "rewrite(h_surj);")
    assert mut_lawvere_rw2 != lawvere_src
    _expect_rejected(
        lambda: parse_and_compile_vr_text(mut_lawvere_rw2, 0),
        TypeCheckError,
        "negative control mutated lawvere_fp.vr (wrong rewrite hypothesis) unexpectedly accepted",
    )
    neg_count += 1

    return results, neg_count


# =============================================================================
# 4. Correspondence Manifest & Track A Structural Checks
# =============================================================================

def verify_correspondence(root: Path, strict_paper_sha: bool = False):
    manifest_path = root / "proofs/afnt-alpha-id/correspondence.json"
    manifest = json.loads(manifest_path.read_text())
    review_path = root / manifest["review"]
    if sha256_bytes(review_path.read_bytes()) != manifest["review_sha256"]:
        raise RuntimeError("correspondence.txt SHA-256 mismatch")

    for item in manifest["formalizations"]:
        fpath = root / item["path"]
        data = fpath.read_bytes()
        if sha256_bytes(data) != item["sha256"]:
            raise RuntimeError(f"formalization SHA-256 mismatch: {item['path']}")
        text = data.decode("utf-8")
        if f"public theorem {item['declaration']}" not in text:
            raise RuntimeError(f"missing declaration {item['declaration']} in {item['path']}")
        # Parse, compile, and typecheck directly from the `.vr` file
        cert = parse_and_compile_vr_text(text, level=0)
        if cert["name"] != item["declaration"]:
            raise RuntimeError(f"parsed declaration mismatch: {cert['name']} vs {item['declaration']}")
        expect_universe((), cert["claimed_type"])
        check((), cert["term"], cert["claimed_type"])

    paper_path = root.parent / manifest["source"]["path"]
    paper_bytes = paper_path.read_bytes()
    paper_sha = sha256_bytes(paper_bytes)
    paper_sha_matched = (paper_sha == manifest["source"]["sha256"])
    if strict_paper_sha and not paper_sha_matched:
        raise RuntimeError("paper-en/paper.tex SHA-256 mismatch")

    offset_matches = True
    for frag in manifest["source"]["fragments"]:
        quote_bytes = frag["quote"].encode("utf-8")
        if sha256_bytes(quote_bytes) != frag["sha256"]:
            raise RuntimeError(f"fragment SHA-256 mismatch for {frag['anchor']}")
        if quote_bytes not in paper_bytes:
            raise RuntimeError(f"fragment quote for {frag['anchor']} not found in {manifest['source']['path']}")
        sliced = paper_bytes[frag["start"]:frag["end"]]
        if sliced != quote_bytes:
            offset_matches = False
            if strict_paper_sha:
                raise RuntimeError(f"fragment byte offset mismatch for {frag['anchor']} ({frag['start']}..{frag['end']})")

    return {
        "paper_sha256_matched": paper_sha_matched,
        "paper_offset_matched": offset_matches,
        "fragments_verified": [f["anchor"] for f in manifest["source"]["fragments"]],
        "formalizations_verified": [f["declaration"] for f in manifest["formalizations"]],
    }


def verify_track_a_structural(root: Path):
    msfs_dir = root / "src/theorems/msfs"
    wave1_files = sorted(msfs_dir.glob("wave1_*.vr"))
    if len(wave1_files) != 4:
        raise RuntimeError(f"expected 4 wave1_*.vr modules, found {len(wave1_files)}")
    mod_text = (msfs_dir / "mod.vr").read_text()
    total_theorems = 0
    details = []
    for p in wave1_files:
        text = p.read_text()
        if re.search(r"^\s*public\s+axiom\b", text, re.M):
            raise RuntimeError(f"forbidden axiom in {p.name}")
        if re.search(r"\bensures\s+true\b", text):
            raise RuntimeError(f"forbidden `ensures true` in {p.name}")
        if re.search(r"^\s*mount\b", text, re.M):
            raise RuntimeError(f"forbidden `mount` import in {p.name}")
        thms = re.findall(r"^\s*public\s+theorem\s+([A-Za-z0-9_]+)", text, re.M)
        if not thms:
            raise RuntimeError(f"no theorems found in {p.name}")
        mod_stem = p.stem
        if f"lib.theorems.msfs.{mod_stem}" not in mod_text:
            raise RuntimeError(f"{mod_stem} not mounted in mod.vr")
        for t in thms:
            if t not in mod_text:
                raise RuntimeError(f"theorem {t} not mounted in mod.vr")
        total_theorems += len(thms)
        details.append({"file": str(p.relative_to(root)), "theorems": thms})
    return {"modules": len(wave1_files), "total_theorems": total_theorems, "details": details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--strict-paper-sha", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    oracle_checks, neg_count = verify_track_b_oracles(args.root)
    corr = verify_correspondence(args.root, strict_paper_sha=args.strict_paper_sha)
    track_a = verify_track_a_structural(args.root)

    replay_bin = shutil.which("verum-source-replay")
    noesis_bin = shutil.which("noesis")

    summary = {
        "profile": "msfs-wave1-verification/2",
        "track_a_structural": track_a,
        "track_b_correspondence": corr,
        "track_b_python_pi_id_oracle": {
            "vr_direct_parse_and_typecheck": True,
            "checked_certificates": len(oracle_checks),
            "negative_controls_rejected": neg_count,
            "details": oracle_checks,
        },
        "external_binaries": {
            "verum_source_replay": replay_bin if replay_bin else "not_run_binary_absent",
            "noesis": noesis_bin if noesis_bin else "not_run_binary_absent",
        },
    }

    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
