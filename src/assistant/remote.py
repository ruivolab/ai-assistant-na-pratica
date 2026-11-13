"""A demo pública: o MCP da Loja Exemplo por HTTP, para ligar no Claude de qualquer pessoa.

Quem pensa é o Claude do visitante. Este servidor só responde às ferramentas: não gasta API.
O balão fica desligado (ele, sim, chamaria a API a cada mensagem). O checkout continua aqui:
a IA cria o link, a pessoa abre e clica em "Pagar".

Rodar: `uvicorn assistant.remote:app --factory` com STORE_PUBLIC_URL=https://mcp.seudominio.com.
"""

import os
import time
from collections import OrderedDict
from urllib.parse import urlparse

from fastapi.responses import JSONResponse

from .app.limits import RateLimit
from .app.main import create_app
from .store import data, server

MAX_VISITORS = 500
SHARED_STORE_SECONDS = 3600
SOLD_OUT_NOTE = "Out of stock: do not offer or suggest it."

# A demo é a vitrine para quem lê em inglês; o app do livro segue com o catálogo em português.
DEMO_PRODUCTS = {
    "cafeteira-italiana": {
        "name": "Moka pot, 6 cups",
        "category": "cafeteiras",
        "price": 189.90,
        "stock": 12,
        "description": "Aluminum, for gas and electric stoves. Does not work on induction.",
        "warranty": "6 months",
        "faq": {"dishwasher safe?": "No. Rinse with water only, no detergent."},
    },
    "prensa-francesa": {
        "name": "French press 1 L",
        "category": "cafeteiras",
        "price": 149.00,
        "stock": 4,
        "description": "Borosilicate glass and stainless steel. Also works for tea.",
        "warranty": "3 months",
        "faq": {"can I replace the glass?": "Yes, the replacement beaker is sold separately."},
    },
    "moedor-manual": {
        "name": "Manual coffee grinder",
        "category": "moedores",
        "price": 259.00,
        "stock": 0,
        "description": "Ceramic burr with 18 grind settings, from espresso to French press.",
        "warranty": "1 year",
        "faq": {},
    },
    "cafe-especial-250g": {
        "name": "Specialty coffee 250 g (whole beans)",
        "category": "cafés",
        "price": 54.00,
        "stock": 40,
        "description": (
            "Arabica from southern Minas Gerais, medium roast, notes of chocolate and caramel."
        ),
        "faq": {"does it come ground?": "No, whole beans."},
    },
}


def demo_store(shared=False):
    return data.new_store(DEMO_PRODUCTS, random_numbers=shared, sold_out_note=SOLD_OUT_NOTE)


class Visitors:
    """Uma loja de mentira por sessão MCP: cada visitante mexe só nos pedidos dele.

    Quem não tem sessão nem login divide uma loja só, que recomeça do zero a cada hora.
    """

    def __init__(self, max_visitors=MAX_VISITORS, clock=time.monotonic):
        self.max_visitors = max_visitors
        self.clock = clock
        self.stores = OrderedDict()
        self.shared = None
        self.shared_since = 0.0

    def store_for(self, session_id):
        if session_id is None:
            return self.shared_store()
        store = self.stores.pop(session_id, None) or demo_store()
        self.stores[session_id] = store
        while len(self.stores) > self.max_visitors:
            _, oldest = self.stores.popitem(last=False)
            data.forget(oldest)  # o link de compra da loja esquecida deixa de valer
        return store

    def shared_store(self):
        if self.shared is None or self.clock() - self.shared_since > SHARED_STORE_SECONDS:
            if self.shared is not None:
                data.forget(self.shared)
            self.shared = demo_store(shared=True)
            self.shared_since = self.clock()
        return self.shared


def limit_calls(app, rate_limit):
    """Teto de chamadas por endereço: sem ele, um robô ocupa o servidor de todo mundo."""

    async def limited(scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "POST":
            client = scope.get("client")
            if not rate_limit.allow(client[0] if client else "?"):
                response = JSONResponse({"error": "Muitas chamadas. Tente mais tarde."}, 429)
                await response(scope, receive, send)
                return
        await app(scope, receive, send)

    return limited


def create_remote_app(public_url=None, rate_limit=None):
    public_url = public_url or os.environ.get("STORE_PUBLIC_URL", "http://localhost:8000")
    server.VISITORS = Visitors()
    server.PUBLIC_URL = public_url
    per_hour = int(os.environ.get("MCP_CALLS_PER_HOUR", "300"))
    rate_limit = rate_limit or RateLimit(max_messages=per_hour, window_seconds=3600)

    mcp_app = server.mcp.http_app(path="/mcp", allowed_hosts=[urlparse(public_url).netloc])
    app = create_app(chat=False, lifespan=mcp_app.lifespan)
    app.mount("/", limit_calls(mcp_app, rate_limit))  # só o /mcp cai aqui
    return app


app = create_remote_app
