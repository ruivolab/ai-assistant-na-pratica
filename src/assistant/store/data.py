"""Loja Exemplo: catálogo e pedidos de mentira, guardados em memória (reiniciou, zerou).

O pagamento é simulado. Ele não é ferramenta da IA: só a página de checkout chama `pay`,
depois do clique da pessoa.
"""

import secrets
from copy import deepcopy

INITIAL_PRODUCTS = {
    "cafeteira-italiana": {
        "name": "Cafeteira italiana 6 xícaras",
        "category": "cafeteiras",
        "price": 189.90,
        "stock": 12,
        "description": "Alumínio, para fogão a gás e elétrico. Não funciona em indução.",
        "warranty": "6 meses",
        "faq": {"vai no lava-louças?": "Não. Lave só com água, sem detergente."},
    },
    "prensa-francesa": {
        "name": "Prensa francesa 1 L",
        "category": "cafeteiras",
        "price": 149.00,
        "stock": 4,
        "description": "Vidro borossilicato e aço inox. Também serve para chá.",
        "warranty": "3 meses",
        "faq": {"o vidro tem reposição?": "Sim, vendemos o copo de reposição separado."},
    },
    "moedor-manual": {
        "name": "Moedor de café manual",
        "category": "moedores",
        "price": 259.00,
        "stock": 0,
        "description": "Mó cerâmica com 18 níveis de moagem, do expresso à prensa francesa.",
        "warranty": "1 ano",
        "faq": {},
    },
    "cafe-especial-250g": {
        "name": "Café especial 250 g (grãos)",
        "category": "cafés",
        "price": 54.00,
        "stock": 40,
        "description": "Arábica do sul de Minas, torra média, notas de chocolate e caramelo.",
        "warranty": "não se aplica",
        "faq": {"vem moído?": "Não, vem em grãos. Para moer na hora, veja o moedor manual."},
    },
}

PRODUCTS = {}
ORDERS = {}
ORDER_BY_TOKEN = {}


def reset():
    PRODUCTS.clear()
    PRODUCTS.update(deepcopy(INITIAL_PRODUCTS))
    ORDERS.clear()
    ORDER_BY_TOKEN.clear()


reset()


def summary(product_id):
    product = PRODUCTS[product_id]
    return {
        "id": product_id,
        "name": product["name"],
        "price": product["price"],
        "available": product["stock"] > 0,
    }


def list_products(category=None):
    return [summary(pid) for pid, p in PRODUCTS.items() if category in (None, p["category"])]


def search_products(term):
    term = term.casefold()
    found = []
    for pid, p in PRODUCTS.items():
        text = f"{p['name']} {p['description']} {p['category']}".casefold()
        if term in text:
            found.append(summary(pid))
    return found


def product_details(product_id):
    product = PRODUCTS.get(product_id)
    if product is None:
        return {"id": product_id, "found": False}
    return {"id": product_id, **deepcopy(product), "available": product["stock"] > 0}


def create_order(product_id, quantity):
    product = PRODUCTS.get(product_id)
    if product is None:
        return {"created": False, "reason": "Produto não existe."}
    if not 1 <= quantity <= 10:
        return {"created": False, "reason": "A quantidade vai de 1 a 10."}
    if product["stock"] < quantity:
        return {"created": False, "reason": f"Só temos {product['stock']} em estoque."}

    number = 1001 + len(ORDERS)
    token = secrets.token_urlsafe(16)  # longo e aleatório: ninguém adivinha o link
    ORDERS[number] = {
        "number": number,
        "product_id": product_id,
        "product": product["name"],
        "quantity": quantity,
        "total": round(product["price"] * quantity, 2),
        "status": "aguardando pagamento",
        "token": token,
    }
    ORDER_BY_TOKEN[token] = number
    return {"created": True, "number": number, "total": ORDERS[number]["total"], "token": token}


def public(order):
    return {key: value for key, value in order.items() if key != "token"}


def order_status(number):
    order = ORDERS.get(number)
    if order is None:
        return {"number": number, "found": False}
    return public(order)


def order_by_token(token):
    number = ORDER_BY_TOKEN.get(token)
    if number is None:
        return None
    return public(ORDERS[number])


def pay(token):
    number = ORDER_BY_TOKEN.get(token)
    if number is None:
        return None
    order = ORDERS[number]
    if order["status"] == "aguardando pagamento":
        product = PRODUCTS[order["product_id"]]
        if product["stock"] < order["quantity"]:
            order["status"] = "sem estoque"
        else:
            product["stock"] -= order["quantity"]
            order["status"] = "pago"
    return public(order)


def cancel_order(number):
    order = ORDERS.get(number)
    if order is None:
        return {"cancelled": False, "reason": "Pedido não existe."}
    if order["status"] == "cancelado":
        return {"cancelled": False, "reason": "O pedido já estava cancelado."}
    if order["status"] == "pago":
        PRODUCTS[order["product_id"]]["stock"] += order["quantity"]  # devolve ao estoque
    order["status"] = "cancelado"
    return {"cancelled": True, **public(order)}
