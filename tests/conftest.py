import copy

import pytest
from fastmcp import Client

from assistant.app.conversation import Assistant
from assistant.app.skills import load
from assistant.store import data, server
from assistant.store.server import mcp

from .paths import SKILLS

CANARY = "CANARIO-teste123"


@pytest.fixture(autouse=True)
def clean_store():
    data.reset()
    server.VISITORS = None  # a demo pública liga a loja por visitante; aqui, a loja única
    server.PUBLIC_URL = None


class ScriptedModel:
    """Faz o papel da API: devolve as respostas do roteiro, na ordem, e guarda o que recebeu."""

    def __init__(self, *turns):
        self.turns = list(turns)
        self.calls = []

    async def respond(self, system, messages, tools):
        self.calls.append({"system": system, "messages": copy.deepcopy(messages)})
        turn = self.turns.pop(0)
        for piece in turn["pieces"]:
            yield "text", piece
        content = []
        if turn["pieces"]:
            content.append({"type": "text", "text": "".join(turn["pieces"])})
        for i, (name, args) in enumerate(turn["tools"]):
            call_id = f"call_{len(self.calls)}_{i}"
            content.append({"type": "tool_use", "id": call_id, "name": name, "input": args})
        stop = turn["stop"] or ("tool_use" if turn["tools"] else "end_turn")
        yield "final", {"content": content, "stop_reason": stop}


def turn(*pieces, tools=None, stop=None):
    return {"pieces": list(pieces), "tools": tools or [], "stop": stop}


def assistant_with(model, server=mcp):
    return Assistant(
        model=model,
        open_mcp=lambda answer: Client(server, elicitation_handler=answer, mode="legacy"),
        skills=load(SKILLS),
        canary=CANARY,
    )
