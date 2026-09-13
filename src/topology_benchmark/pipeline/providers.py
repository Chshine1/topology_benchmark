import base64
import json
import os
from dataclasses import dataclass
from typing import Protocol, override
from urllib.request import Request, urlopen

from topology_benchmark.core.models import QuestionSection
from topology_benchmark.pipeline.config import ProviderConfig


class ModelProvider(Protocol):
    @property
    def identity(self) -> str: ...

    def answer(self, question: str, sections: tuple[QuestionSection, ...]) -> str: ...


@dataclass(slots=True)
class FixedProvider(ModelProvider):
    response: str

    @property
    @override
    def identity(self) -> str:
        return "fixed"

    @override
    def answer(self, question: str, sections: tuple[QuestionSection, ...]) -> str:
        del question, sections
        return self.response


@dataclass(slots=True)
class OpenAICompatibleProvider(ModelProvider):
    config: ProviderConfig

    @property
    @override
    def identity(self) -> str:
        return self.config.model

    @override
    def answer(self, question: str, sections: tuple[QuestionSection, ...]) -> str:
        api_key = os.environ.get(self.config.api_key_env)
        if not api_key:
            raise RuntimeError(f"missing API key environment variable {self.config.api_key_env}")
        content: list[dict[str, object]] = [{"type": "text", "text": _instruction(question)}]
        for section in sections:
            encoded = base64.b64encode(section.content.encode()).decode()
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{section.media_type};base64,{encoded}"},
                }
            )
        body = json.dumps(
            {
                "model": self.config.model,
                "messages": [{"role": "user", "content": content}],
                "temperature": 0,
            }
        ).encode()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            **self.config.extra_headers,
        }
        endpoint = self.config.base_url.rstrip("/") + "/chat/completions"
        request = Request(endpoint, data=body, headers=headers, method="POST")
        with urlopen(request, timeout=self.config.timeout_seconds) as response:
            result = json.loads(response.read())
        return str(result["choices"][0]["message"]["content"])


def build_provider(config: ProviderConfig) -> ModelProvider:
    if config.kind == "fixed":
        return FixedProvider(config.fixed_response)
    return OpenAICompatibleProvider(config)


def _instruction(question: str) -> str:
    return (
        f"{question}\n\nSolve the problem from the supplied diagram(s). "
        "End with a line in exactly this form: FINAL_ANSWER: <answer>"
    )
