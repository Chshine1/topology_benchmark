import base64
import json
from dataclasses import dataclass
from typing import Protocol, override
from urllib.request import Request, urlopen

from attrs import field, frozen

from topology_benchmark.core.problem.models import QuestionSection
from topology_benchmark.core.validation import nonblank
from topology_benchmark.pipeline.config import OpenAICompatibleModelProviderConfig

OPENAI_COMPATIBLE_PROVIDER_VERSION = "openai-compatible-chat-v1"


class IModelProvider(Protocol):
    def answer(self, question: str, sections: tuple[QuestionSection, ...]) -> str: ...


@frozen
class OpenAICompatibleModelProviderCredentials:
    api_key: str = field(validator=nonblank("a model provider API key cannot be blank"))


@dataclass(slots=True)
class OpenAICompatibleModelProvider(IModelProvider):
    config: OpenAICompatibleModelProviderConfig
    credentials: OpenAICompatibleModelProviderCredentials

    @override
    def answer(self, question: str, sections: tuple[QuestionSection, ...]) -> str:
        content: list[dict[str, object]] = [
            {
                "type": "text",
                "text": (
                    f"{question}\n\nSolve the problem from the supplied diagram(s). "
                    "End with a line in exactly this form: FINAL_ANSWER: <answer>"
                ),
            }
        ]
        for section in sections:
            if section.media_type == "text/plain":
                content.append({"type": "text", "text": section.content})
                continue
            if section.media_type.startswith("image/"):
                encoded = base64.b64encode(section.content.encode()).decode()
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{section.media_type};base64,{encoded}"},
                    }
                )
                continue
            raise ValueError(
                f"the OpenAI-compatible provider does not support {section.media_type!r} sections"
            )
        body = json.dumps(
            {
                "model": self.config.model,
                "messages": [{"role": "user", "content": content}],
                "temperature": 0,
            }
        ).encode()
        headers = {
            "Authorization": f"Bearer {self.credentials.api_key}",
            "Content-Type": "application/json",
            **self.config.extra_headers,
        }
        endpoint = self.config.base_url.rstrip("/") + "/chat/completions"
        request = Request(endpoint, data=body, headers=headers, method="POST")
        with urlopen(request, timeout=self.config.timeout_seconds) as response:
            result = json.loads(response.read())
        return str(result["choices"][0]["message"]["content"])
