"""A cabeça: a chamada à API da Anthropic, com a resposta chegando aos pedaços (streaming)."""

import os

import anthropic


class ClaudeModel:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic()  # lê a ANTHROPIC_API_KEY do ambiente
        self.model = os.environ.get("ASSISTANT_MODEL", "claude-opus-5-5")
        self.effort = os.environ.get("ASSISTANT_EFFORT", "low")
        self.fallback = os.environ.get("ASSISTANT_FALLBACK", "1") == "1"

    async def respond(self, system, messages, tools):
        request = {
            "model": self.model,
            "max_tokens": 16000,
            "system": system,
            "messages": messages,
            "tools": tools,
        }
        # vazio: não manda (um provedor compatível com a API pode não conhecer o campo)
        if self.effort:
            request["output_config"] = {"effort": self.effort}
        if self.fallback:
            # se o modelo recusar por engano, a própria API tenta outro modelo na mesma chamada
            request["betas"] = ["server-side-fallback-2026-07-01"]
            request["fallbacks"] = "default"

        async with self.client.beta.messages.stream(**request) as stream:
            async for event in stream:
                if event.type == "text":
                    yield "text", event.text
            final = await stream.get_final_message()

        blocks = [block.model_dump(mode="json", exclude_none=True) for block in final.content]
        yield "final", {"content": blocks, "stop_reason": final.stop_reason}
