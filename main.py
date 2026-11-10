import json
import uuid

import anthropic
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

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

PRODUCTS = [
    {"name": "Cafeteira italiana 6 xícaras", "price": 189.90},
    {"name": "Prensa francesa 1 L", "price": 149.00},
]

TOOLS = [{
    "name": "list_products",
    "description": "Lista os produtos da loja, com preço.",
    "input_schema": {"type": "object", "properties": {}},
}]


def run_tool(name, args):
    if name == "list_products":
        return json.dumps(PRODUCTS, ensure_ascii=False)
    return "Essa ferramenta não existe."


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
        while True:
            with client.messages.stream(
                model="claude-opus-5-5", max_tokens=16000,
                system=INSTRUCTIONS, messages=history, tools=TOOLS,
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
                results.append({
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": run_tool(call.name, call.input),
                })
            history.append({"role": "user", "content": results})

        yield sse("suggestions", SUGGESTIONS)

    headers = {"X-Conversation": conversation_id}
    return StreamingResponse(
        pieces(), media_type="text/event-stream", headers=headers
    )
