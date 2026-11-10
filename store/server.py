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


if __name__ == "__main__":
    mcp.run()
