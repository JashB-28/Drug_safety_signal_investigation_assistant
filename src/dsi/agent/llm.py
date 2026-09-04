"""Local LLM client (Ollama) behind a tiny protocol so tests inject a fake.

The only thing the rest of the system needs from a model is: given a fully-built
prompt string, return text plus token counts. Ollama's `/api/generate` returns
`prompt_eval_count` (input tokens) and `eval_count` (output tokens), which feed the
metrics spine directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResponse:
    text: str
    tokens_in: int
    tokens_out: int


class LLMClient(Protocol):
    def complete(self, prompt: str, *, temperature: float = 0.0) -> LLMResponse: ...


class OllamaClient:
    """Real client. Pinned model tag comes from settings for reproducibility."""

    def __init__(self, model_tag: str, host: str = "http://localhost:11434") -> None:
        import ollama
        self.model_tag = model_tag
        self._client = ollama.Client(host=host)

    def complete(self, prompt: str, *, temperature: float = 0.0) -> LLMResponse:
        resp = self._client.generate(
            model=self.model_tag,
            prompt=prompt,
            options={"temperature": temperature},
            stream=False,
        )
        return LLMResponse(
            text=resp.get("response", ""),
            tokens_in=int(resp.get("prompt_eval_count", 0) or 0),
            tokens_out=int(resp.get("eval_count", 0) or 0),
        )


class ScriptedLLM:
    """Test double. Resolution order per call: (1) first matching `route` whose
    substring is in the prompt, (2) next queued response, (3) the default. Records
    prompts so tests can assert what the model was (and was not) shown."""

    def __init__(self, responses: list[str] | None = None, default: str = "{}",
                 routes: list[tuple[str, str]] | None = None,
                 tokens_in: int = 10, tokens_out: int = 5) -> None:
        self._responses = list(responses or [])
        self._default = default
        self._routes = list(routes or [])
        self._ti = tokens_in
        self._to = tokens_out
        self.prompts: list[str] = []

    def complete(self, prompt: str, *, temperature: float = 0.0) -> LLMResponse:
        self.prompts.append(prompt)
        for substring, response in self._routes:
            if substring in prompt:
                return LLMResponse(text=response, tokens_in=self._ti, tokens_out=self._to)
        text = self._responses.pop(0) if self._responses else self._default
        return LLMResponse(text=text, tokens_in=self._ti, tokens_out=self._to)
