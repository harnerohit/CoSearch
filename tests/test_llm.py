"""Step 6: complete_json retry behaviour with a mocked client (no network)."""

from types import SimpleNamespace

import httpx2
import pytest
from openai import AuthenticationError, InternalServerError

import src.llm as llm
from src import config
from src.llm import LLMError, complete_json

REQUEST = httpx2.Request("POST", "https://example.test/v1/chat/completions")


def _response(content, finish_reason="stop"):
    """Build an object shaped like the SDK's ChatCompletion (duck-typed)."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish_reason)]
    )


def _timeout():
    return llm.APITimeoutError(request=REQUEST)


def _rate_limited():
    return llm.RateLimitError(
        "rate limited", response=httpx2.Response(429, request=REQUEST), body=None
    )


def _connection():
    return llm.APIConnectionError(message="connection error", request=REQUEST)


def _bad_json_validated():
    return llm.BadRequestError(
        "Error code: 400 - {'error': {'code': 'json_validate_failed', 'failed_generation': ''}}",
        response=httpx2.Response(400, request=REQUEST),
        body={"error": {"code": "json_validate_failed", "message": "Failed to validate JSON."}},
    )


def _bad_request(message="Error code: 400 - {'error': {'code': 'invalid_param'}}"):
    return llm.BadRequestError(
        message, response=httpx2.Response(400, request=REQUEST), body={"error": {"code": "invalid_param"}}
    )


@pytest.fixture
def fake_llm(monkeypatch):
    """Patch OpenAI and time.sleep; outcomes are consumed one per create() call."""
    state = SimpleNamespace(outcomes=[], calls=[], slept=[], client_kwargs=None)

    class FakeCompletions:
        def create(self, **kwargs):
            state.calls.append(kwargs)
            outcome = state.outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        def __init__(self, **kwargs):
            state.client_kwargs = kwargs
            self.chat = FakeChat()

    monkeypatch.setattr(llm, "OpenAI", FakeClient)
    monkeypatch.setattr(llm.time, "sleep", state.slept.append)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    return state


def test_returns_json_on_first_try(fake_llm):
    fake_llm.outcomes = [_response('{"ok": true}')]
    assert complete_json("sys", "user") == {"ok": True}
    assert len(fake_llm.calls) == 1
    kwargs = fake_llm.calls[0]
    assert kwargs["model"] == "test-model"
    assert kwargs["temperature"] == config.LLM_TEMPERATURE
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["reasoning_effort"] == config.LLM_REASONING_EFFORT
    assert kwargs["max_tokens"] == config.LLM_MAX_TOKENS
    assert "json" in kwargs["messages"][0]["content"].lower()
    client = fake_llm.client_kwargs
    assert client["api_key"] == "test-key"
    assert client["base_url"] == "https://example.test/v1"
    assert client["timeout"] == config.LLM_TIMEOUT_SECONDS
    assert client["max_retries"] == 0
    assert fake_llm.slept == []


def test_invalid_json_retries_once_then_succeeds(fake_llm):
    fake_llm.outcomes = [_response("{not json"), _response('{"ok": true}')]
    assert complete_json("sys", "user") == {"ok": True}
    assert len(fake_llm.calls) == 2
    assert fake_llm.slept == [config.LLM_BACKOFF_SECONDS]


def test_invalid_json_twice_raises_after_one_retry(fake_llm):
    fake_llm.outcomes = [_response("{not json"), _response("{also not json")]
    with pytest.raises(LLMError):
        complete_json("sys", "user")
    assert len(fake_llm.calls) == 2


def test_json_array_is_not_accepted(fake_llm):
    fake_llm.outcomes = [_response("[1, 2]"), _response("[1, 2]")]
    with pytest.raises(LLMError):
        complete_json("sys", "user")
    assert len(fake_llm.calls) == 2


def test_empty_content_retries_then_raises(fake_llm):
    fake_llm.outcomes = [_response(""), _response("")]
    with pytest.raises(LLMError):
        complete_json("sys", "user")
    assert len(fake_llm.calls) == 2


def test_truncated_answer_is_a_failure(fake_llm):
    fake_llm.outcomes = [
        _response('{"ok": tr', finish_reason="length"),
        _response('{"ok": tr', finish_reason="length"),
    ]
    with pytest.raises(LLMError):
        complete_json("sys", "user")
    assert len(fake_llm.calls) == 2


def test_no_choices_is_a_failure(fake_llm):
    empty = SimpleNamespace(choices=[])
    fake_llm.outcomes = [empty, empty]
    with pytest.raises(LLMError):
        complete_json("sys", "user")
    assert len(fake_llm.calls) == 2


def test_timeout_retries_then_succeeds(fake_llm):
    fake_llm.outcomes = [_timeout(), _response('{"ok": true}')]
    assert complete_json("sys", "user") == {"ok": True}
    assert len(fake_llm.calls) == 2
    assert fake_llm.slept == [config.LLM_BACKOFF_SECONDS]


def test_persistent_rate_limit_raises_after_two_retries(fake_llm):
    fake_llm.outcomes = [_rate_limited(), _rate_limited(), _rate_limited()]
    with pytest.raises(LLMError):
        complete_json("sys", "user")
    assert len(fake_llm.calls) == config.LLM_MAX_RETRIES + 1
    assert len(fake_llm.slept) == config.LLM_MAX_RETRIES


def test_persistent_connection_error_raises_after_two_retries(fake_llm):
    fake_llm.outcomes = [_connection(), _connection(), _connection()]
    with pytest.raises(LLMError):
        complete_json("sys", "user")
    assert len(fake_llm.calls) == config.LLM_MAX_RETRIES + 1


def test_json_validate_failed_retries_then_succeeds(fake_llm):
    fake_llm.outcomes = [_bad_json_validated(), _response('{"ok": true}')]
    assert complete_json("sys", "user") == {"ok": True}
    assert len(fake_llm.calls) == 2


def test_json_validate_failed_twice_raises(fake_llm):
    fake_llm.outcomes = [_bad_json_validated(), _bad_json_validated()]
    with pytest.raises(LLMError):
        complete_json("sys", "user")
    assert len(fake_llm.calls) == 2


def test_other_bad_request_raises_without_retry(fake_llm):
    fake_llm.outcomes = [_bad_request()]
    with pytest.raises(LLMError):
        complete_json("sys", "user")
    assert len(fake_llm.calls) == 1
    assert fake_llm.slept == []


def test_authentication_error_becomes_llm_error_without_retry(fake_llm):
    fake_llm.outcomes = [
        AuthenticationError(
            "Error code: 401 - invalid api key",
            response=httpx2.Response(401, request=REQUEST),
            body=None,
        )
    ]
    with pytest.raises(LLMError):
        complete_json("sys", "user")
    assert len(fake_llm.calls) == 1
    assert fake_llm.slept == []


def test_internal_server_error_becomes_llm_error_without_retry(fake_llm):
    fake_llm.outcomes = [
        InternalServerError(
            "Error code: 500 - internal server error",
            response=httpx2.Response(500, request=REQUEST),
            body=None,
        )
    ]
    with pytest.raises(LLMError):
        complete_json("sys", "user")
    assert len(fake_llm.calls) == 1
    assert fake_llm.slept == []


def test_missing_api_key_raises_without_calling_the_client(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    with pytest.raises(LLMError) as excinfo:
        complete_json("sys", "user")
    assert "LLM_API_KEY" in str(excinfo.value)
