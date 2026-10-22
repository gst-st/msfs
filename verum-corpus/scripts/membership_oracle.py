#!/usr/bin/env python3
"""Independent named-AST oracle for the MSFS representation-membership lemma.

It uses only Pi/Id, with no axioms, library imports, assumed memberships, or
semantic equivalence of categories.  Named binders are compiled to de Bruijn
indices independently of Verum's source elaborator.
"""
import json


def V(name): return ('var', name)
def U(level): return ('universe', level)
def Pi(name, domain, codomain): return ('pi', name, domain, codomain)
def Lam(name, domain, body): return ('lam', name, domain, body)
def App(fn, arg): return ('app', fn, arg)
def Id(carrier, lhs, rhs): return ('id', carrier, lhs, rhs)

def chain(kind, binders, body):
    for name, domain in reversed(binders):
        body = kind(name, domain, body)
    return body

def syntactic_branch():
    return Pi('phi', V('Syn'), Pi('presentation',
        Id(V('Obj'), App(V('point'), V('phi')), V('X')), V('R')))

def formal(level):
    return Pi('R', U(level), Pi('syntactic', syntactic_branch(), V('R')))

def derived(level):
    return chain(Pi, [
        ('R', U(level)),
        ('syntactic', syntactic_branch()),
        ('semantic', Pi('semantic_member', App(V('SemanticLocal'), V('X')), V('R'))),
        ('global', Pi('global_member', App(V('Global'), V('X')), V('R'))),
    ], V('R'))

def compile_named(term, scope=()):
    kind = term[0]
    if kind == 'var':
        if term[1] not in scope:
            raise ValueError(f'free variable {term[1]} in {scope}')
        return {'Var': scope[::-1].index(term[1])}
    if kind == 'universe': return {'Universe': {'Concrete': term[1]}}
    if kind in ('pi', 'lam'):
        _, name, domain, body = term
        return {'Pi' if kind == 'pi' else 'Lam': [
            compile_named(domain, scope), compile_named(body, (*scope, name))]}
    if kind == 'app': return {'App': [compile_named(term[1], scope), compile_named(term[2], scope)]}
    if kind == 'id':
        return {'Id': dict(zip(('ty', 'lhs', 'rhs'),
            (compile_named(x, scope) for x in term[1:])))}
    raise ValueError(kind)

def certificate(level, witness_form=False):
    parameters = [
        ('Obj', U(level)), ('Syn', U(level)),
        ('point', Pi('phi', V('Syn'), V('Obj'))),
        ('SemanticLocal', Pi('x', V('Obj'), U(level))),
        ('Global', Pi('x', V('Obj'), U(level))),
        ('X', V('Obj')),
    ]
    if witness_form:
        hypothesis = [('phi0', V('Syn')), ('presentation0',
            Id(V('Obj'), App(V('point'), V('phi0')), V('X')))]
        conclusion_term = App(App(V('syntactic'), V('phi0')), V('presentation0'))
    else:
        hypothesis = [('definition', formal(level))]
        conclusion_term = App(App(V('definition'), V('R')), V('syntactic'))
    eliminators = [
        ('R', U(level)), ('syntactic', syntactic_branch()),
        ('semantic', Pi('semantic_member', App(V('SemanticLocal'), V('X')), V('R'))),
        ('global', Pi('global_member', App(V('Global'), V('X')), V('R'))),
    ]
    return {
        'term': compile_named(chain(Lam, parameters + hypothesis + eliminators, conclusion_term)),
        'claimed_type': compile_named(chain(Pi, parameters + hypothesis, derived(level))),
        'metadata': {
            'theorem': 'msfs_syntactic_presentation_in_derived_union',
            'source_anchor': 'paper-en/paper.tex:lem:SS-membership',
            'scope': 'representation-level syntactic branch; no F3 semantic equivalence',
            'encoding': 'predicative Church elimination into Type@u; no converse equivalence claimed',
            'universe': str(level),
            'form': 'explicit-presentation' if witness_form else 'encoded-formal-definability',
            'oracle': 'independent named AST to de Bruijn; not Verum elaborator output',
        }
    }

