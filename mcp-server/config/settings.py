from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from enums import AudioFormat, LlmProvider, PollyEngine

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
    cors_origins: list[str] = []


class LlmSettings(Section):
    model_config = SettingsConfigDict(env_prefix="LLM_")

    provider: LlmProvider = LlmProvider.OPENROUTER
    max_tokens: int = 300
    temperature: float = 0


class MockSettings(Section):
    model_config = SettingsConfigDict(env_prefix="MOCK_")

    answers_path: Path = PROJECT_ROOT / "data" / "mock_answers.json"


class MemorySettings(Section):
    model_config = SettingsConfigDict(env_prefix="MEMORY_")

    db_path: Path = PROJECT_ROOT / "data" / "memory.db"
    company_id: str = "demo"
    unfinished_ttl_hours: float = 24
    recent_messages: int = 10
    summary_trigger_words: int = 400


class SessionSettings(Section):
    model_config = SettingsConfigDict(env_prefix="SESSION_")

    ttl_hours: float = 720


class SosSettings(Section):
    model_config = SettingsConfigDict(env_prefix="SOS_")

    countdown_seconds: int = 5
    cooldown_minutes: float = 2


class PauseSettings(Section):
    """How long Alexa waits after the person stops talking before she answers, learned per person."""

    model_config = SettingsConfigDict(env_prefix="PAUSE_")

    start_seconds: float = 2
    min_seconds: float = 1.5
    max_seconds: float = 6
    # Added each time Alexa answered before the person had finished, until enough pauses are measured.
    step_seconds: float = 0.5
    # A longer pause isn't a pause in a sentence (a cough, someone talking to them), so it isn't counted.
    ignore_over_seconds: float = 10
    keep: int = 20
    min_samples: int = 5
    margin: float = 1.2


class TelegramSettings(Section):
    model_config = SettingsConfigDict(env_prefix="TELEGRAM_")

    bot_token: SecretStr | None = None
    api_url: str = "https://api.telegram.org"
    # How long one request for new messages waits on Telegram's side before it is asked again.
    poll_seconds: int = 25
    timeout_seconds: float = 10

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.bot_token.get_secret_value())


class LocationSettings(Section):
    model_config = SettingsConfigDict(env_prefix="LOCATION_")

    enabled: bool = True
    language: str = "en"
    # An emergency alert waits at most this long for the address; after that it goes with the map link only.
    timeout_seconds: float = 2
    region: str = Field(default="us-east-1", validation_alias="AWS_REGION")


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


class TranscribeSettings(Section):
    model_config = SettingsConfigDict(env_prefix="TRANSCRIBE_")

    path: str = "/transcribe"
    language_code: str = "en-US"
    sample_rate_hz: int = 16000
    region: str = Field(default="us-east-1", validation_alias="AWS_REGION")


class PollySettings(Section):
    model_config = SettingsConfigDict(env_prefix="POLLY_")

    path: str = "/speak"
    voice_id: str = "Joanna"
    engine: PollyEngine = PollyEngine.NEURAL
    output_format: AudioFormat = AudioFormat.MP3
    region: str = Field(default="us-east-1", validation_alias="AWS_REGION")


class GroqSettings(Section):
    model_config = SettingsConfigDict(env_prefix="GROQ_")

    api_key: SecretStr | None = None
    model_id: str = "openai/gpt-oss-120b"
    base_url: str = "https://api.groq.com/openai/v1/chat/completions"
    timeout_seconds: float = 30
    reasoning_effort: str = "low"


class Settings(BaseModel):
    server: ServerSettings = Field(default_factory=ServerSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    mock: MockSettings = Field(default_factory=MockSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    session: SessionSettings = Field(default_factory=SessionSettings)
    sos: SosSettings = Field(default_factory=SosSettings)
    pause: PauseSettings = Field(default_factory=PauseSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    location: LocationSettings = Field(default_factory=LocationSettings)
    bedrock: BedrockSettings = Field(default_factory=BedrockSettings)
    openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)
    groq: GroqSettings = Field(default_factory=GroqSettings)
    transcribe: TranscribeSettings = Field(default_factory=TranscribeSettings)
    polly: PollySettings = Field(default_factory=PollySettings)


@lru_cache
def get_settings() -> Settings:
    return Settings()
