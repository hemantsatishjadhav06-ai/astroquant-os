"""
Knowledge graph + research-note export for the Market Genome Project.

Turns a battery of `Finding`s into a queryable graph (condition → outcome edges, weighted by effect
and graded by verdict) and renders it as JSON, a Mermaid diagram, and a Markdown research note — the
"research papers / signal library / knowledge graph" outputs of Idea 2.
"""
from __future__ import annotations

from datetime import datetime, timezone

from astroquant.genome.studies import Finding, GenomeReport


class KnowledgeGraph:
    def __init__(self) -> None:
        self.nodes: set[str] = set()
        self.edges: list[dict] = []

    def add_finding(self, f: Finding) -> None:
        self.nodes.add(f.predictor)
        self.nodes.add(f.outcome)
        self.edges.append({
            "from": f.predictor, "to": f.outcome, "effect": f.effect,
            "q_value": f.q_value, "verdict": f.verdict, "study": f.id,
        })

    @classmethod
    def from_report(cls, report: GenomeReport) -> "KnowledgeGraph":
        g = cls()
        for f in report.findings:
            g.add_finding(f)
        return g

    def to_dict(self) -> dict:
        return {"nodes": sorted(self.nodes), "edges": self.edges}

    def to_mermaid(self) -> str:
        lines = ["graph LR"]
        for e in self.edges:
            rel = e["verdict"] == "relationship"
            style = "==>" if rel else "-.->"
            label = f"r={e['effect']:+.2f}, q={e['q_value']:.2f}"
            a = e["from"].replace(" ", "_")
            b = e["to"].replace(" ", "_")
            lines.append(f'  {a}["{e["from"]}"] {style}|"{label}"| {b}["{e["to"]}"]')
        return "\n".join(lines)

    def to_markdown(self, report: GenomeReport) -> str:
        gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        rel = [f for f in report.findings if f.verdict == "relationship"]
        head = (
            f"# Market Genome — {report.symbol} ({report.source})\n\n"
            f"_Generated {gen} · {report.meta.get('n_samples', '?')} samples · "
            f"{report.meta.get('start')}→{report.meta.get('end')} · "
            f"permutation n={report.meta.get('n_perm')} · FDR-corrected (Benjamini–Hochberg)_\n\n"
            f"**{report.n_relationships} of {report.n_studies}** tested relationships survived "
            f"multiple-testing correction.\n\n"
        )
        if rel:
            head += "## Relationships found\n\n"
            for f in rel:
                head += f"- **{f.predictor} → {f.outcome}**: r={f.effect:+.3f}, q={f.q_value:.3f} ({f.question})\n"
            head += "\n"
        else:
            head += ("## Relationships found\n\n_None survived correction._ On the tested window the "
                     "honest conclusion is that these conditions carry no robust relationship to the "
                     "outcomes — a genuine knowledge result, recorded as a null.\n\n")
        head += "## All studies\n\n| Study | Condition | Outcome | r | q (FDR) | Verdict |\n|---|---|---|---:|---:|---|\n"
        for f in report.findings:
            head += f"| {f.id} | {f.predictor} | {f.outcome} | {f.effect:+.3f} | {f.q_value:.3f} | {f.verdict} |\n"
        head += "\n## Knowledge graph (Mermaid)\n\n```mermaid\n" + self.to_mermaid() + "\n```\n"
        head += ("\n> Method controls (RSI→reversal, weekday, momentum) are included so the battery's "
                 "sensitivity is visible: if even these show nothing, the window is simply uninformative.\n")
        return head
