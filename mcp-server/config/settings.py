from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from enums import LlmProvider

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Section(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


class ServerSettings(Section):
    model_config = SettingsConfigDict(env_prefix="MCP_")

    name: str = "speech-resilient-alexa"
    transport: str = "streamable-http"
    host: str = "127.0.0.1"
    port: int = 8000
    path: str = "/mcp"


class LlmSettings(Section):
    model_config = SettingsConfigDict(env_prefix="LLM_")

    provider: LlmProvider = LlmProvider.MOCK
    max_tokens: int = 300
    temperature: float = 0


class MockSettings(Section):
    model_config = SettingsConfigDict(env_prefix="MOCK_")

    answers_path: Path = PROJECT_ROOT / "data" / "mock_answers.json"


class BedrockSettings(Section):
    model_config = SettingsConfigDict(env_prefix="BEDROCK_")

    model_id: str = "amazon.nova-lite-v1:0"
    region: str = Field(default="us-east-1", validation_alias="AWS_REGION")


class OpenRouterSettings(Section):
    model_config = SettingsConfigDict(env_prefix="OPENROUTER_")

    api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "OPENROUTER"),
    )
    model_id: str = "google/gemini-3.1-flash-lite"
    base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    timeout_seconds: float = 30
    app_title: str = "Speech-Resilient Alexa"


class Settings(BaseModel):
    server: ServerSettings = Field(default_factory=ServerSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    mock: MockSettings = Field(default_factory=MockSettings)
    bedrock: BedrockSettings = Field(default_factory=BedrockSettings)
    openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)


@lru_cache
def get_settings() -> Settings:
    return Settings()
