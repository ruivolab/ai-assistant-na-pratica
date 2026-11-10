import json

import anthropic
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

app = FastAPI()
client = anthropic.Anthropic()

INSTRUCTIONS = """Você é o assistente da Loja Exemplo, de café.
Responda em português, curto e simpático.
- Confirme o que entendeu só quando houver dúvida.
- Resolva e termine com um próximo passo.
- Se não souber, diga que não sabe."""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def page():
    return FileResponse("index.html")


@app.post("/api/chat")
def chat(body: dict):
    message = body["message"]

    def pieces():
        with client.messages.stream(
            model="claude-opus-5-5",
            max_tokens=16000,
            system=INSTRUCTIONS,
            messages=[{"role": "user", "content": message}],
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps(text)}\n\n"

    return StreamingResponse(
        pieces(), media_type="text/event-stream"
    )
