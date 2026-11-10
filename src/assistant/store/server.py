"""As mãos do assistente: o servidor MCP da Loja Exemplo, feito com FastMCP.

O app web usa este servidor no mesmo processo.
Para ligar no Claude Desktop, rode `uv run store-mcp`.
"""

import os
from pathlib import Path

from fastmcp import Context, FastMCP

from . import data, docs
from .rules import CHANGE, PREPARE, READ, person_said_yes

mcp = FastMCP("Loja Exemplo")
DOCS_DIR = Path(os.environ.get("DOCS_DIR", Path(__file__).parents[3] / "docs"))
PIECES = docs.load_pieces(DOCS_DIR)


@mcp.tool(**READ)
def list_products(category: str | None = None) -> list[dict]:
    """Produtos da Loja Exemplo, com preço e se há estoque.

    Categorias: cafeteiras, moedores, cafés.
    """
    return data.list_products(category)


@mcp.tool(**READ)
def search_products(term: str) -> list[dict]:
    """Procura produtos pelo nome, pela descrição ou pela categoria."""
    return data.search_products(term)


@mcp.tool(**READ)
def product_details(product_id: str) -> dict:
    """Tudo o que a loja sabe de um produto.

    Preço, estoque, descrição, garantia e perguntas frequentes.
    """
    return data.product_details(product_id)


@mcp.tool(**READ)
def order_status(number: int) -> dict:
    """Produto, quantidade, total e status de um pedido.

    O status é aguardando pagamento, pago ou cancelado.
    """
    return data.order_status(number)


@mcp.tool(**READ)
def search_docs(question: str) -> list[dict]:
    """Busca nos textos da loja: trocas, devolução, frete e manuais de uso.

    Devolve até 3 trechos, cada um com a fonte. Responda só com o que eles dizem e cite a fonte.
    Lista vazia: diga que não encontrou.
    """
    return docs.search(PIECES, question)


@mcp.tool(**PREPARE)
def create_purchase_link(product_id: str, quantity: int = 1) -> dict:
    """Cria um pedido aguardando pagamento e devolve o link do checkout.

    Nada é cobrado aqui: quem paga é a pessoa, na página do link.
    """
    order = data.create_order(product_id, quantity)
    if not order["created"]:
        return order
    base_url = os.environ.get("STORE_PUBLIC_URL", "http://localhost:8000")
    token = order.pop("token")
    return {**order, "link": f"{base_url}/checkout/{token}"}


@mcp.tool(**CHANGE)
async def cancel_order(number: int, ctx: Context) -> dict:
    """Cancela um pedido da Loja Exemplo. A pessoa precisa autorizar."""
    if not await person_said_yes(ctx, f"Cancelar o pedido {number}?"):
        return {"done": False, "reason": "Sem o sim da pessoa, nada mudou."}
    return data.cancel_order(number)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
