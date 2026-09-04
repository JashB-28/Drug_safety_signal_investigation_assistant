"""Prompt-injection defense --- tool layer.

Untrusted retrieved text may contain instruction-like strings. Here we prove the
TOOLS capture such a string verbatim as typed DATA (in a field), never acting on
it. The end-to-end confirmation that the AGENT ignores the instruction (it enters
the model only inside a delimited data field) is added in Phase 6 once the context
builder and model call exist; this test locks down the retrieval half.
"""

from __future__ import annotations

from dsi.domain.tools import FaersSearchRequest, LabelFetchRequest
from dsi.mcp_server.openfda import fetch_drug_label, search_adverse_events


def test_faers_injection_string_captured_as_inert_data(http):
    client = http.Client([http.ok(http.faers(with_injection=True))])
    res = search_adverse_events(FaersSearchRequest(drug="montelukast"), client)
    assert res.ok is True
    injected = res.data.reports[-1]
    # The instruction-like text lands in a DATA field (drug indication), unchanged,
    # and the tool's own behaviour is unaffected (it still parsed all 3 reports).
    assert injected.drugs[0].indication == http.INJECTION
    assert res.data.returned == 3


def test_label_injection_string_stays_in_text_field(http):
    client = http.Client([http.ok(http.label(with_injection=True))])
    res = fetch_drug_label(LabelFetchRequest(drug="montelukast"), client)
    assert res.ok is True
    boxed = next(s for s in res.data.sections if s.section.value == "boxed_warning")
    # Captured verbatim inside the section text; it is data, not a command.
    assert http.INJECTION in boxed.text
