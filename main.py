import asyncio
import json
import uuid
from pathlib import Path

import anthropic
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastmcp import Client

from store.server import ORDERS, mcp

app = FastAPI()
client = anthropic.Anthropic()
conversations = {}

INSTRUCTIONS = """Você é o assistente da Loja Exemplo, de café.
Responda em português, curto e simpático.
- Confirme o que entendeu só quando houver dúvida.
- Resolva e termine com um próximo passo.
- Se não souber, diga que não sabe."""

SUGGESTIONS = [
    "Ver os produtos", "Posso trocar um produto?", "Quero comprar",
]


def load_skills(folder):
    skills = {}
    for file in Path(folder).glob("*/SKILL.md"):
        _, header, steps = file.read_text().split("---", 2)
        meta = yaml.safe_load(header)
        skills[meta["name"]] = {
            "description": meta["description"],
            "steps": steps.strip(),
        }
    return skills


SKILLS = load_skills("skills")
CATALOG = ""
for name, skill in SKILLS.items():
    CATALOG += f"- {name}: {skill['description']}\n"
SYSTEM = INSTRUCTIONS + "\n\nSkills:\n" + CATALOG

OPEN_SKILL = {
    "name": "open_skill",
    "description": "Abre o passo a passo de uma skill da lista.",
    "input_schema": {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
}


async def store_tools():
    async with Client(mcp) as store:
        tools = await store.list_tools()
    return [{"name": t.name, "description": t.description,
             "input_schema": t.input_schema} for t in tools]


async def call_store(name, args):
    async with Client(mcp) as store:
        result = await store.call_tool(name, args)
    return json.dumps(result.data, ensure_ascii=False)


def run_tool(name, args):
    if name == "open_skill":
        skill = SKILLS.get(args["name"])
        return skill["steps"] if skill else "Essa skill não existe."
    return asyncio.run(call_store(name, args))


def sse(kind, data):
    return f"event: {kind}\ndata: {json.dumps(data)}\n\n"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def page():
    return FileResponse("index.html")


@app.post("/api/chat")
def chat(body: dict):
    conversation_id = body.get("conversation") or uuid.uuid4().hex
    history = conversations.setdefault(conversation_id, [])
    history.append({"role": "user", "content": body["message"]})

    def pieces():
        tools = asyncio.run(store_tools()) + [OPEN_SKILL]
        while True:
            with client.messages.stream(
                model="claude-opus-5-5", max_tokens=16000,
                system=SYSTEM, messages=history, tools=tools,
            ) as stream:
                for text in stream.text_stream:
                    yield sse("text", text)
                answer = stream.get_final_message()
            history.append(
                {"role": "assistant", "content": answer.content}
            )
            calls = [b for b in answer.content if b.type == "tool_use"]
            if not calls:
                break
            results = []
            for call in calls:
                result = run_tool(call.name, call.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": result,
                })
                if call.name == "create_purchase_link":
                    yield sse("link", json.loads(result))
            history.append({"role": "user", "content": results})

        yield sse("suggestions", SUGGESTIONS)

    headers = {"X-Conversation": conversation_id}
    return StreamingResponse(
        pieces(), media_type="text/event-stream", headers=headers
    )


@app.get("/checkout/{token}", response_class=HTMLResponse)
def checkout(token: str):
    order = ORDERS.get(token)
    if order is None:
        raise HTTPException(404, "Link inválido.")
    return f"""<h1>Pedido {order['number']}</h1>
<p>{order['quantity']} x {order['product']}:
R$ {order['total']:.2f}</p>
<form method="post" action="/checkout/{token}/pay">
  <button>Pagar</button></form>"""


@app.post("/checkout/{token}/pay", response_class=HTMLResponse)
def pay(token: str):
    order = ORDERS.get(token)
    if order is None:
        raise HTTPException(404, "Link inválido.")
    order["status"] = "pago"
    return "<h1>Pago!</h1><p>Pagamento simulado.</p>"
