"""Drug Safety Signal Investigation Assistant (dsi).

An open-source, agentic pharmacovigilance assistant that investigates a
drug + suspected adverse event and produces an evidence-backed memo for
human review.

Design principle enforced throughout the package layout:
three kinds of data are kept physically separate ---
  (a) raw retrieved evidence      -> `dsi.domain.evidence`   (never edited by the LLM)
  (b) deterministic analysis      -> `dsi.domain.analysis`   (plain tested Python)
  (c) LLM-generated prose (memo)  -> `dsi.domain.memo`       (rebuildable from a + b)
"""

__version__ = "0.1.0"
