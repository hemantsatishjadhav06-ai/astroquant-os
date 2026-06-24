"""Tests for Idea 2 — the Market Genome Project (relationship studies + knowledge graph)."""
from datetime import date

import numpy as np

from astroquant.genome import KnowledgeGraph, run_genome
from astroquant.genome.studies import STUDIES, _corr, _permutation_p


def test_genome_runs_and_grades():
    rep = run_genome("NIFTY", source="synthetic", start=date(2018, 1, 1),
                     end=date(2022, 12, 31), n_perm=60)
    assert rep.n_studies == len(STUDIES)
    for f in rep.findings:
        assert 0.0 <= f.q_value <= 1.0
        assert f.verdict in ("relationship", "no_relationship")
    # On a random-walk synthetic series, essentially nothing should survive FDR.
    assert rep.n_relationships <= 1


def test_permutation_detects_and_rejects():
    rng = np.random.default_rng(0)
    n = 400
    x = rng.standard_normal(n)
    y_signal = x * 0.6 + rng.standard_normal(n) * 0.5     # genuinely correlated
    y_noise = rng.standard_normal(n)                       # unrelated
    p_signal = _permutation_p(x, y_signal, _corr(x, y_signal), n_perm=200, seed=1)
    p_noise = _permutation_p(x, y_noise, _corr(x, y_noise), n_perm=200, seed=1)
    assert p_signal < 0.05          # real relationship detected
    assert p_noise > 0.05           # noise correctly not significant


def test_knowledge_graph_exports():
    rep = run_genome("NIFTY", source="synthetic", start=date(2019, 1, 1),
                     end=date(2021, 12, 31), n_perm=40)
    g = KnowledgeGraph.from_report(rep)
    assert g.edges and g.nodes
    assert g.to_mermaid().startswith("graph LR")
    md = g.to_markdown(rep)
    assert "Market Genome" in md and "Knowledge graph" in md


def test_determinism():
    a = run_genome("NIFTY", source="synthetic", start=date(2019, 1, 1), end=date(2021, 12, 31), n_perm=40)
    b = run_genome("NIFTY", source="synthetic", start=date(2019, 1, 1), end=date(2021, 12, 31), n_perm=40)
    assert [f.effect for f in a.findings] == [f.effect for f in b.findings]
