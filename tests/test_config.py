from pathlib import Path

import pytest
from pydantic import ValidationError

from config import Settings


def test_each_section_reads_its_own_env_prefix(monkeypatch):
    monkeypatch.setenv("MCP_PORT", "9123")
    monkeypatch.setenv("MCP_PATH", "/speech")
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    monkeypatch.setenv("LLM_MAX_TOKENS", "64")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "amazon.nova-micro-v1:0")
    monkeypatch.setenv("OPENROUTER_MODEL_ID", "some/model")

    settings = Settings()

    assert settings.server.port == 9123
    assert settings.server.path == "/speech"
    assert settings.llm.provider == "bedrock"
    assert settings.llm.max_tokens == 64
    assert settings.bedrock.region == "eu-west-1"
    assert settings.bedrock.model_id == "amazon.nova-micro-v1:0"
    assert settings.openrouter.model_id == "some/model"


@pytest.mark.parametrize("variable", ["OPENROUTER_API_KEY", "OPENROUTER"])
def test_openrouter_key_accepts_both_names(monkeypatch, variable):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER", raising=False)
    monkeypatch.setenv(variable, "secret")

    assert Settings().openrouter.api_key.get_secret_value() == "secret"


def test_polly_reads_its_voice_and_shares_the_aws_region(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    monkeypatch.setenv("POLLY_VOICE_ID", "Matthew")
    monkeypatch.setenv("POLLY_ENGINE", "generative")
    monkeypatch.setenv("POLLY_OUTPUT_FORMAT", "ogg_vorbis")

    polly = Settings().polly

    assert polly.region == "eu-west-1"
    assert polly.voice_id == "Matthew"
    assert polly.engine == "generative"
    assert polly.output_format.media_type == "audio/ogg"


@pytest.mark.parametrize("variable, value", [("POLLY_ENGINE", "fast"), ("POLLY_OUTPUT_FORMAT", "wav")])
def test_unknown_polly_values_are_rejected(monkeypatch, variable, value):
    monkeypatch.setenv(variable, value)

    with pytest.raises(ValidationError):
        Settings()


def test_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")

    with pytest.raises(ValidationError):
        Settings()


def test_env_example_lists_every_setting():
    example = (Path(__file__).resolve().parents[1] / ".env.example").read_text()
    sections = Settings().model_dump()
    prefixes = {
        "server": "MCP_",
        "llm": "LLM_",
        "memory": "MEMORY_",
        "sos": "SOS_",
        "yes_no": "YES_NO_",
        "pause": "PAUSE_",
        "telegram": "TELEGRAM_",
        "location": "LOCATION_",
        "bedrock": "BEDROCK_",
        "openrouter": "OPENROUTER_",
        "groq": "GROQ_",
        "transcribe": "TRANSCRIBE_",
        "polly": "POLLY_",
        "session": "SESSION_",
    }
    aliases = {
        ("bedrock", "region"): "AWS_REGION",
        ("transcribe", "region"): "AWS_REGION",
        ("polly", "region"): "AWS_REGION",
        ("location", "region"): "AWS_REGION",
    }

    for section, fields in sections.items():
        if section == "mock":
            continue
        for field in fields:
            name = aliases.get((section, field), f"{prefixes[section]}{field.upper()}")
            assert f"{name}=" in example
