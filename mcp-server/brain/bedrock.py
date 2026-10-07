import json
from pathlib import Path

import boto3

from brain.schemas import BrainResult
from config import Settings, get_settings


SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "understand_speech.txt").read_text()


class BedrockBrain:
    def __init__(self, settings: Settings | None = None) -> None:
        config = settings or get_settings()
        self._client = boto3.client("bedrock-runtime", region_name=config.bedrock.region)
        self._model_id = config.bedrock.model_id
        self._max_tokens = config.llm.max_tokens
        self._temperature = config.llm.temperature

    def interpret(self, fragments: list[str]) -> BrainResult:
        response = self._client.converse(
            modelId=self._model_id,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": json.dumps({"fragments": fragments})}],
                }
            ],
            inferenceConfig={"maxTokens": self._max_tokens, "temperature": self._temperature},
        )
        text = response["output"]["message"]["content"][0]["text"]
        return BrainResult.model_validate_json(text)
