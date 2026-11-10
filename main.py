import anthropic
from fastapi import FastAPI

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


@app.post("/api/chat")
def chat(body: dict):
    message = body["message"]
    answer = client.messages.create(
        model="claude-opus-5-5", max_tokens=16000,
        system=INSTRUCTIONS,
        messages=[{"role": "user", "content": message}],
    )
    text = ""
    for block in answer.content:
        if block.type == "text":
            text += block.text
    return {"text": text}
