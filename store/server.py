from fastmcp import FastMCP

PRODUCTS = [
    {"name": "Cafeteira italiana 6 xícaras", "price": 189.90},
    {"name": "Prensa francesa 1 L", "price": 149.00},
]
mcp = FastMCP("Loja Exemplo")


@mcp.tool
def list_products() -> list[dict]:
    """Lista os produtos da loja, com preço."""
    return PRODUCTS


@mcp.tool
def product_details(name: str) -> dict:
    """Tudo o que a loja sabe de um produto, pelo nome."""
    for product in PRODUCTS:
        if name.lower() in product["name"].lower():
            return product
    return {"found": False}


import os
import secrets

ORDERS = {}
STORE_PUBLIC_URL = os.environ.get(
    "STORE_PUBLIC_URL", "http://localhost:8000")


def find_product(name):
    for product in PRODUCTS:
        if name.lower() in product["name"].lower():
            return product
    return None


@mcp.tool
def create_purchase_link(name: str, quantity: int = 1) -> dict:
    """Cria um pedido aguardando pagamento e devolve o link.
    Nada é cobrado aqui: quem paga é a pessoa, na página do link."""
    product = find_product(name)
    if product is None:
        return {"created": False, "reason": "Produto não existe."}
    token = secrets.token_urlsafe(16)
    ORDERS[token] = {
        "number": 1001 + len(ORDERS),
        "product": product["name"],
        "quantity": quantity,
        "total": product["price"] * quantity,
        "status": "aguardando pagamento",
    }
    link = f"{STORE_PUBLIC_URL}/checkout/{token}"
    return {"created": True, **ORDERS[token], "link": link}


import re
import unicodedata
from pathlib import Path

DOCS = Path(__file__).parent.parent / "docs"


def load_pieces():
    pieces = []
    for path in sorted(DOCS.glob("*.md")):
        texts = path.read_text(encoding="utf-8").split("\n\n")
        for number, text in enumerate(texts, 1):
            source = f"{path.name} §{number}"
            pieces.append({"source": source, "text": text.strip()})
    return pieces


PIECES = load_pieces()


def roots(text):
    plain = unicodedata.normalize("NFKD", text.lower())
    plain = plain.encode("ascii", "ignore").decode()
    return {word[:5] for word in re.findall(r"\w{4,}", plain)}


@mcp.tool
def search_docs(question: str) -> list[dict]:
    """Busca nos textos da loja: trocas, frete e manuais.
    Responda só com o que os trechos dizem e cite a fonte
    entre colchetes, como [trocas.md §1].
    Lista vazia: diga que não encontrou."""
    wanted = roots(question)
    found = []
    for piece in PIECES:
        score = len(wanted & roots(piece["text"]))
        if score > 0:
            found.append((score, piece))
    found.sort(key=lambda pair: pair[0], reverse=True)
    return [piece for score, piece in found[:3]]


if __name__ == "__main__":
    mcp.run()
