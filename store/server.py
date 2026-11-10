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


if __name__ == "__main__":
    mcp.run()
