"""Loja Exemplo: catálogo e pedidos de mentira, guardados em memória (reiniciou, zerou).

O pagamento é simulado. Ele não é ferramenta da IA: só a página de checkout chama `pay`,
depois do clique da pessoa.
"""

import secrets
from contextlib import contextmanager
from contextvars import ContextVar
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
DEFAULT_STORE = {"products": PRODUCTS, "orders": ORDERS, "by_token": ORDER_BY_TOKEN}

# Na demo pública, cada visitante tem a própria loja; o app do livro usa sempre a DEFAULT_STORE.
_current = ContextVar("store", default=DEFAULT_STORE)
STORE_OF_TOKEN = {}  # o checkout chega só com o token: é ele que diz de qual loja é o pedido


def new_store(products=INITIAL_PRODUCTS, random_numbers=False, sold_out_note=None):
    return {
        "products": deepcopy(products),
        "orders": {},
        "by_token": {},
        "random_numbers": random_numbers,
        "sold_out_note": sold_out_note,
    }


@contextmanager
def using(store):
    token = _current.set(store)
    try:
        yield store
    finally:
        _current.reset(token)


def forget(store):
    for token in store["by_token"]:
        STORE_OF_TOKEN.pop(token, None)


def reset():
    PRODUCTS.clear()
    PRODUCTS.update(deepcopy(INITIAL_PRODUCTS))
    ORDERS.clear()
    ORDER_BY_TOKEN.clear()
    STORE_OF_TOKEN.clear()


reset()


def _products():
    return _current.get()["products"]


def _orders():
    return _current.get()["orders"]


def _with_sold_out_note(product, answer):
    note = _current.get().get("sold_out_note")
    if note and product["stock"] == 0:
        answer["note"] = note
    return answer


def summary(product_id):
    product = _products()[product_id]
    answer = {
        "id": product_id,
        "name": product["name"],
        "price": product["price"],
        "available": product["stock"] > 0,
    }
    return _with_sold_out_note(product, answer)


def list_products(category=None):
    return [summary(pid) for pid, p in _products().items() if category in (None, p["category"])]


def search_products(term):
    term = term.casefold()
    found = []
    for pid, p in _products().items():
        text = f"{p['name']} {p['description']} {p['category']}".casefold()
        if term in text:
            found.append(summary(pid))
    return found


def product_details(product_id):
    product = _products().get(product_id)
    if product is None:
        return {"id": product_id, "found": False}
    answer = {"id": product_id, **deepcopy(product), "available": product["stock"] > 0}
    return _with_sold_out_note(product, answer)


def create_order(product_id, quantity):
    store = _current.get()
    product = store["products"].get(product_id)
    if product is None:
        return {"created": False, "reason": "Produto não existe."}
    if not 1 <= quantity <= 10:
        return {"created": False, "reason": "A quantidade vai de 1 a 10."}
    if product["stock"] < quantity:
        return {"created": False, "reason": f"Só temos {product['stock']} em estoque."}

    orders = store["orders"]
    number = 1001 + len(orders)
    while store.get("random_numbers") and (number < 100_000 or number in orders):
        # loja dividida: o número em sequência diria quantos pediram e abriria o pedido do outro
        number = 100_000 + secrets.randbelow(900_000)
    token = secrets.token_urlsafe(16)  # longo e aleatório: ninguém adivinha o link
    orders[number] = {
        "number": number,
        "product_id": product_id,
        "product": product["name"],
        "quantity": quantity,
        "total": round(product["price"] * quantity, 2),
        "status": "aguardando pagamento",
        "token": token,
    }
    store["by_token"][token] = number
    STORE_OF_TOKEN[token] = store
    return {"created": True, "number": number, "total": orders[number]["total"], "token": token}


def public(order):
    return {key: value for key, value in order.items() if key != "token"}


def order_status(number):
    order = _orders().get(number)
    if order is None:
        return {"number": number, "found": False}
    return public(order)


def _store_and_order(token):
    store = STORE_OF_TOKEN.get(token)
    if store is None:
        return None, None
    return store, store["orders"][store["by_token"][token]]


def order_by_token(token):
    _, order = _store_and_order(token)
    return None if order is None else public(order)


def pay(token):
    store, order = _store_and_order(token)
    if order is None:
        return None
    if order["status"] == "aguardando pagamento":
        product = store["products"][order["product_id"]]
        if product["stock"] < order["quantity"]:
            order["status"] = "sem estoque"
        else:
            product["stock"] -= order["quantity"]
            order["status"] = "pago"
    return public(order)


def cancel_order(number):
    order = _orders().get(number)
    if order is None:
        return {"cancelled": False, "reason": "Pedido não existe."}
    if order["status"] == "cancelado":
        return {"cancelled": False, "reason": "O pedido já estava cancelado."}
    if order["status"] == "pago":
        _products()[order["product_id"]]["stock"] += order["quantity"]  # devolve ao estoque
    order["status"] = "cancelado"
    return {"cancelled": True, **public(order)}
