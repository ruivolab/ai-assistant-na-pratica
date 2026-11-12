"""O servidor web: o balão conversa só com ele. A chave da API mora aqui, nunca no navegador."""

import html
import json
import logging
import os
import secrets
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastmcp import Client

from ..store import data
from ..store.server import mcp
from .conversation import Assistant, Conversation
from .limits import MAX_MESSAGE_LENGTH, RateLimit
from .skills import load

log = logging.getLogger("assistant")
STATIC = Path(__file__).parent / "static"
SKILLS_DIR = Path(os.environ.get("SKILLS_DIR", Path(__file__).parents[3] / "skills"))
MAX_CONVERSATIONS = 1000


def open_store_mcp(who_answers_the_person):
    # mode="legacy": o protocolo MCP 2025-11-25, o mesmo do Claude Desktop,
    # em que a ferramenta consegue perguntar à pessoa
    return Client(mcp, elicitation_handler=who_answers_the_person, mode="legacy")


def real_assistant():
    from .model import ClaudeModel

    return Assistant(
        model=ClaudeModel(),
        open_mcp=open_store_mcp,
        skills=load(SKILLS_DIR),
        canary=f"CANARIO-{secrets.token_hex(4)}",
    )


def sse(kind, payload):
    return f"event: {kind}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def read_json(request: Request):
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "Mande um JSON.") from None
    if not isinstance(body, dict):
        raise HTTPException(400, "Mande um objeto JSON.")
    return body


def create_app(assistant=None, rate_limit=None, chat=True, lifespan=None):
    app = FastAPI(title="Loja Exemplo", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    per_hour = int(os.environ.get("ASSISTANT_MESSAGES_PER_HOUR", "30"))
    rate_limit = rate_limit or RateLimit(max_messages=per_hour, window_seconds=3600)
    conversations = {}
    state = {"assistant": assistant}  # o de verdade só nasce na primeira mensagem

    def get_assistant():
        if state["assistant"] is None:
            state["assistant"] = real_assistant()
        return state["assistant"]

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/")
    def shop():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/products")
    def products():
        return data.list_products()

    @app.post("/api/chat")
    async def chat_message(request: Request):
        if not chat:
            raise HTTPException(503, "O balão está desligado nesta demo. Use o servidor MCP.")
        body = await read_json(request)
        message = str(body.get("message", "")).strip()
        if not 0 < len(message) <= MAX_MESSAGE_LENGTH:
            raise HTTPException(
                422, f"A mensagem precisa ter de 1 a {MAX_MESSAGE_LENGTH} caracteres."
            )
        visitor = request.client.host if request.client else "?"
        if not rate_limit.allow(visitor):
            raise HTTPException(429, "Muitas mensagens. Tente de novo mais tarde.")

        conversation_id = body.get("conversation")
        if conversation_id not in conversations:
            if len(conversations) >= MAX_CONVERSATIONS:
                conversations.pop(next(iter(conversations)))  # esquece a mais antiga
            conversation_id = uuid.uuid4().hex
            conversations[conversation_id] = Conversation()
        conversation = conversations[conversation_id]
        assistant = get_assistant()

        async def events():
            yield sse("conversation", {"id": conversation_id})
            try:
                async for kind, payload in assistant.chat(conversation, message):
                    yield sse(kind, payload)
            except Exception:
                log.exception("a conversa falhou")
                yield sse("error", "Tive um problema aqui. Pode tentar de novo?")
            yield sse("end", {})

        headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        return StreamingResponse(events(), media_type="text/event-stream", headers=headers)

    @app.post("/api/confirm")
    async def confirm(request: Request):
        if not chat:
            raise HTTPException(503, "O balão está desligado nesta demo. Use o servidor MCP.")
        body = await read_json(request)
        conversation = conversations.get(body.get("conversation"))
        if conversation is None:
            raise HTTPException(404, "Conversa não encontrada.")
        allow = body.get("allow") is True
        return await get_assistant().confirm(conversation, str(body.get("id")), allow)

    @app.get("/checkout/{token}", response_class=HTMLResponse)
    def checkout(token: str):
        order = data.order_by_token(token)  # abrir o link só MOSTRA o pedido
        if order is None:
            raise HTTPException(404, "Link de compra inválido.")
        return checkout_page(token, order)

    @app.post("/checkout/{token}/pay", response_class=HTMLResponse)
    def pay(token: str):
        order = data.pay(token)  # só o clique no botão (um POST) paga
        if order is None:
            raise HTTPException(404, "Link de compra inválido.")
        return checkout_page(token, order)

    return app


def money(value):
    return "R$ " + f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def checkout_page(token, order):
    if order["status"] == "aguardando pagamento":
        action = f"""<form method="post" action="/checkout/{html.escape(token)}/pay">
  <button>Pagar {money(order["total"])}</button></form>
<p class="note">Pagamento simulado: nenhum dinheiro de verdade passa por aqui.</p>"""
    else:
        status = html.escape(order["status"])
        action = f'<p>Status: <b>{status}</b></p><a href="/">Voltar para a loja</a>'
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Checkout · Loja Exemplo</title>
<link rel="stylesheet" href="/static/style.css"></head><body class="checkout"><main>
<h1>Pedido {order["number"]}</h1>
<p>{order["quantity"]} x {html.escape(order["product"])}</p>
<p class="total">{money(order["total"])}</p>
{action}
</main></body></html>"""


app = create_app()
