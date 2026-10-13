import boto3
from pydantic import BaseModel

from config import Settings
from enums import ChatRole


class BedrockClient:
    def __init__(self, settings: Settings) -> None:
        self._client = boto3.client("bedrock-runtime", region_name=settings.bedrock.region)
        self._model_id = settings.bedrock.model_id
        self._llm = settings.llm

    def complete(self, system: str, user: str, schema: type[BaseModel] | None = None) -> str:
        response = self._client.converse(
            modelId=self._model_id,
            system=[{"text": system}],
            messages=[{"role": ChatRole.USER, "content": [{"text": user}]}],
            inferenceConfig={"maxTokens": self._llm.max_tokens, "temperature": self._llm.temperature},
        )
        return response["output"]["message"]["content"][0]["text"]
