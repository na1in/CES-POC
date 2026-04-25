from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ingest import parse_reference_fields


def _mock_claude_response(json_text: str):
    """Build a fake Anthropic response object returning the given text."""
    content_block = MagicMock()
    content_block.text = json_text
    response = MagicMock()
    response.content = [content_block]
    return response


# ── Claude returns clean structured data ─────────────────────────────────────

async def test_parse_extracts_policy_number():
    mock_response = _mock_claude_response(
        '{"extracted_policy_number": "POL-00001", "payment_intent": "premium", "period_count": 1}'
    )
    with patch("app.services.ingest._get_client") as mock_get_client:
        mock_get_client.return_value.messages.create = AsyncMock(return_value=mock_response)
        result = await parse_reference_fields("for policy POL-00001 April payment", None)

    assert result["extracted_policy_number"] == "POL-00001"
    assert result["payment_intent"] == "premium"
    assert result["period_count"] == 1


async def test_parse_detects_arrears_intent():
    mock_response = _mock_claude_response(
        '{"extracted_policy_number": null, "payment_intent": "arrears", "period_count": 1}'
    )
    with patch("app.services.ingest._get_client") as mock_get_client:
        mock_get_client.return_value.messages.create = AsyncMock(return_value=mock_response)
        result = await parse_reference_fields("catching up on missed payments", None)

    assert result["payment_intent"] == "arrears"
    assert result["extracted_policy_number"] is None


async def test_parse_detects_multi_period():
    mock_response = _mock_claude_response(
        '{"extracted_policy_number": "POL-00002", "payment_intent": "premium", "period_count": 3}'
    )
    with patch("app.services.ingest._get_client") as mock_get_client:
        mock_get_client.return_value.messages.create = AsyncMock(return_value=mock_response)
        result = await parse_reference_fields("3 months premium POL-00002", None)

    assert result["period_count"] == 3


async def test_parse_combines_both_reference_fields():
    """Both ref fields should be joined and sent to Claude together."""
    mock_response = _mock_claude_response(
        '{"extracted_policy_number": "POL-00003", "payment_intent": "partial", "period_count": 1}'
    )
    with patch("app.services.ingest._get_client") as mock_get_client:
        mock_create = AsyncMock(return_value=mock_response)
        mock_get_client.return_value.messages.create = mock_create
        await parse_reference_fields("policy POL-00003", "partial payment")

    call_args = mock_create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert "POL-00003" in prompt
    assert "partial payment" in prompt


# ── Fallback behaviour ────────────────────────────────────────────────────────

async def test_parse_returns_defaults_on_timeout():
    with patch("app.services.ingest._get_client") as mock_get_client:
        mock_get_client.return_value.messages.create = AsyncMock(
            side_effect=TimeoutError("Claude timed out")
        )
        result = await parse_reference_fields("some reference text", None)

    assert result == {"extracted_policy_number": None, "payment_intent": "unknown", "period_count": 1}


async def test_parse_returns_defaults_on_invalid_json():
    mock_response = _mock_claude_response("Sorry, I cannot process this request.")
    with patch("app.services.ingest._get_client") as mock_get_client:
        mock_get_client.return_value.messages.create = AsyncMock(return_value=mock_response)
        result = await parse_reference_fields("some reference text", None)

    assert result == {"extracted_policy_number": None, "payment_intent": "unknown", "period_count": 1}


async def test_parse_skips_claude_when_both_fields_empty():
    """No API call should be made if both reference fields are None."""
    with patch("app.services.ingest._get_client") as mock_get_client:
        result = await parse_reference_fields(None, None)
        mock_get_client.assert_not_called()

    assert result == {"extracted_policy_number": None, "payment_intent": "unknown", "period_count": 1}
