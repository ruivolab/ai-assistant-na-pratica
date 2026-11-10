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
        with client.messages.stream(
            model="claude-opus-5-5", max_tokens=16000,
            system=INSTRUCTIONS, messages=history,
        ) as stream:
            for text in stream.text_stream:
                yield sse("text", text)
            answer = stream.get_final_message()
        history.append({"role": "assistant", "content": answer.content})
        yield sse("suggestions", SUGGESTIONS)

    headers = {"X-Conversation": conversation_id}
    return StreamingResponse(
        pieces(), media_type="text/event-stream", headers=headers
    )
