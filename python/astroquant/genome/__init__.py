"""
Market Genome Project (Idea 2) — knowledge discovery, not trading.

Builds a library of *tested relationships* between market-behaviour conditions (moon phase, Gann
cycles, retrogrades, weekday, RSI, …) and outcomes (next-day direction, volatility, reversal), each
with an effect size, a permutation p-value, a batch-wide FDR-corrected q-value, and a verdict. The
findings populate a queryable knowledge graph and an auto-generated research note.

Example questions it answers honestly:
  * Does Moon illumination affect next-day volatility?
  * Do Gann time-cycles predict reversals?
  * Does Mercury retrograde shift mean returns?
The output is knowledge (a signal library + graph), not a trade.
"""
from astroquant.genome.knowledge import KnowledgeGraph
from astroquant.genome.studies import Finding, GenomeReport, run_genome

__all__ = ["Finding", "GenomeReport", "run_genome", "KnowledgeGraph"]
