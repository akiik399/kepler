import json
import logging
import re
from typing import Any

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from graphiti_core.llm_client.errors import RefusalError
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.llm_client.openai_base_client import ModelSize

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict[str, Any] | None:
    """Try to extract a JSON object from text, handling markdown and partial output."""
    if not text:
        return None
    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(line for line in lines if not line.strip().startswith("```")).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Find JSON object with regex (handles embedded JSON in reasoning text)
    for match in re.finditer(r"\{.*\}", text, re.DOTALL):
        candidate = match.group()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


class DeepSeekClient(OpenAIClient):
    """Custom OpenAIClient for DeepSeek reasoning models.

    DeepSeek v4 models are reasoning models and may embed JSON in
    reasoning_content rather than content. They also don't support
    OpenAI's structured output beta API.
    """

    async def _create_completion(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        temperature: float | None,
        max_tokens: int,
        response_model: type[BaseModel] | None = None,
        reasoning: str | None = None,
        verbosity: str | None = None,
    ) -> Any:
        kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        return await self.client.chat.completions.create(**kwargs)

    async def _create_structured_completion(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        max_tokens: int,
        response_model: type[BaseModel] | None = None,
        reasoning: str | None = None,
        verbosity: str | None = None,
        **kwargs,
    ) -> Any:
        return await self._create_completion(
            model=model,
            messages=messages,
            temperature=kwargs.get("temperature"),
            max_tokens=max_tokens + 4096,
        )

    async def _generate_response(
        self,
        messages: list,
        response_model: type[BaseModel] | None = None,
        max_tokens: int = 16384,
        model_size: ModelSize = ModelSize.medium,
    ) -> tuple[dict[str, Any], int, int]:
        openai_messages = self._convert_messages_to_openai_format(messages)
        model = self._get_model_for_size(model_size)

        # Instruct model to output JSON
        if response_model is not None:
            schema = json.dumps(response_model.model_json_schema())
            instruction = (
                f"\n\nYou MUST output ONLY valid JSON matching this schema, with no other text:\n{schema}"
            )
            if openai_messages:
                last = openai_messages[-1]
                last["content"] = (last.get("content", "") + instruction)

        response = await self.client.chat.completions.create(
            model=model,
            messages=openai_messages,
            temperature=self.temperature,
            max_tokens=(max_tokens or self.max_tokens) + 8192,
            response_format={"type": "json_object"} if response_model else None,
        )

        return self._handle_structured_response(response)

    def _handle_structured_response(self, response: Any) -> tuple[dict[str, Any], int, int]:
        message = response.choices[0].message if response.choices else None
        content = (message.content or "").strip() if message else ""
        reasoning = (message.reasoning_content or "").strip() if hasattr(message, "reasoning_content") else ""

        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage") and response.usage:
            input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(response.usage, "completion_tokens", 0) or 0

        # Try content first, then reasoning_content
        parsed = _extract_json(content) or _extract_json(reasoning)
        if parsed:
            return parsed, input_tokens, output_tokens

        if message and getattr(message, "refusal", None):
            raise RefusalError(message.refusal)

        logger.warning(
            "Could not extract JSON from DeepSeek response. content=%s reasoning=%s",
            content[:100], reasoning[:100],
        )
        return {"content": content or reasoning}, input_tokens, output_tokens
