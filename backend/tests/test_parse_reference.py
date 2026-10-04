import pytest

from app.services.ingest import parse_reference_fields

DEFAULTS = {"extracted_policy_number": None, "payment_intent": "unknown", "period_count": 1}


@pytest.mark.parametrize("ref1, ref2, expected", [
    # well-formed
    ("for policy POL-00001 April payment", None, "POL-00001"),
    ("POL-90001", None, "POL-90001"),
    # missing hyphen / spacing / punctuation variants are normalised to POL-XXXXX (the LLM parser returned "POL90001")
    ("POL90001", None, "POL-90001"),
    ("ref POL90001", "monthly auto", "POL-90001"),
    ("pol 90003 - ins.", None, "POL-90003"),
    ("Pol.93010 - prem", None, "POL-93010"),
    ("pol-91006", "home premium", "POL-91006"),
    ("Policy #90014", None, "POL-90014"),
    # "policy no." phrasings
    ("policy no. 90014", "LIFE POLICY PAYMENT", "POL-90014"),
    ("pmt for policy no. 90004", "annual premium", "POL-90004"),
    ("ins. policy no. 10169", "MEDICAL PLAN", "POL-10169"),
    ("policy number: 90014", None, "POL-90014"),
    ("P0L-90001", None, "POL-90001"),
    # the number may be in either field; the same policy repeated is still one policy
    ("premium", "policy POL-00003", "POL-00003"),
    ("POL-90001 / pol 90001", None, "POL-90001"),
])
async def test_parse_extracts_and_normalises_policy_number(ref1, ref2, expected):
    result = await parse_reference_fields(ref1, ref2)
    assert result["extracted_policy_number"] == expected


@pytest.mark.parametrize("ref1, ref2", [
    ("policyholder 90014", None),      # keyword must not run into letters
    ("police report 12345", None),
    ("invoice 12345", None),          # a bare 5-digit number is not a policy number
    ("POL-9000", None),               # too short
    ("POL-900011", None),             # too long
    ("thanks", "payment"),
    ("catching up on missed payments", None),
    ("some reference text", None),
])
async def test_parse_does_not_invent_a_policy_number(ref1, ref2):
    assert (await parse_reference_fields(ref1, ref2))["extracted_policy_number"] is None


async def test_parse_two_different_policies_is_left_unmatched():
    """Ambiguous: an analyst chooses, rather than silently taking the first."""
    result = await parse_reference_fields("POL-90001 and POL-90002", None)
    assert result["extracted_policy_number"] is None


async def test_parse_combines_both_reference_fields():
    result = await parse_reference_fields("policy", "no. 90014")
    assert result["extracted_policy_number"] == "POL-90014"


async def test_parse_returns_defaults_when_both_fields_empty():
    assert await parse_reference_fields(None, None) == DEFAULTS
    assert await parse_reference_fields("", "   ") == DEFAULTS


async def test_parse_is_deterministic_and_makes_no_network_call():
    """The ingest-time parse and the pipeline's parse must agree (finding F2), and parsing costs nothing."""
    first = await parse_reference_fields("ins. policy no. 10169", "MEDICAL PLAN")
    for _ in range(20):
        assert await parse_reference_fields("ins. policy no. 10169", "MEDICAL PLAN") == first
    import app.services.ingest as ingest
    assert not hasattr(ingest, "_get_client")  # no LLM client left in the module
