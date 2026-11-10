import asyncio

from fastmcp import Client

from assistant.store import data
from assistant.store.rules import kind_of, tools_without_kind
from assistant.store.server import mcp


async def person_says_yes(*_):
    return True


async def person_says_no(*_):
    return False


def call(name, args, person=person_says_yes):
    async def run():
        async with Client(mcp, elicitation_handler=person, mode="legacy") as client:
            return (await client.call_tool(name, args)).data

    return asyncio.run(run())


def kinds():
    async def run():
        async with Client(mcp) as client:
            return {tool.name: kind_of(tool) for tool in await client.list_tools()}

    return asyncio.run(run())


def test_the_store_offers_exactly_the_tools_of_the_book():
    assert kinds() == {
        "list_products": "read",
        "search_products": "read",
        "product_details": "read",
        "order_status": "read",
        "search_docs": "read",
        "create_purchase_link": "prepare",
        "cancel_order": "change",
    }


def test_every_tool_has_a_kind():
    assert asyncio.run(tools_without_kind(mcp)) == []


def test_details_come_from_the_catalog():
    press = call("product_details", {"product_id": "prensa-francesa"})

    assert press["price"] == 149.00
    assert press["available"] is True
    assert call("product_details", {"product_id": "nope"}) == {"id": "nope", "found": False}


def test_the_purchase_link_charges_nothing():
    link = call("create_purchase_link", {"product_id": "cafeteira-italiana", "quantity": 2})

    assert "/checkout/" in link["link"]
    order = data.order_status(link["number"])
    assert order["status"] == "aguardando pagamento"
    assert "token" not in order
    assert data.PRODUCTS["cafeteira-italiana"]["stock"] == 12


def test_sold_out_product_gets_no_link():
    assert call("create_purchase_link", {"product_id": "moedor-manual"})["created"] is False
    assert data.ORDERS == {}


def test_paying_marks_paid_and_takes_stock_only_once():
    order = data.create_order("prensa-francesa", 3)

    assert data.pay(order["token"])["status"] == "pago"
    assert data.pay(order["token"])["status"] == "pago"
    assert data.PRODUCTS["prensa-francesa"]["stock"] == 1
    assert data.pay("unknown-token") is None


def test_cancel_happens_only_with_the_persons_yes():
    number = data.create_order("cafe-especial-250g", 1)["number"]

    assert call("cancel_order", {"number": number}, person_says_no)["done"] is False
    assert data.order_status(number)["status"] == "aguardando pagamento"

    assert call("cancel_order", {"number": number})["cancelled"] is True
    assert data.order_status(number)["status"] == "cancelado"


def test_an_app_that_cannot_ask_cancels_nothing():
    number = data.create_order("cafe-especial-250g", 1)["number"]

    async def without_question():
        async with Client(mcp, mode="legacy") as client:
            return (await client.call_tool("cancel_order", {"number": number})).data

    assert asyncio.run(without_question())["done"] is False
    assert data.order_status(number)["status"] == "aguardando pagamento"


def test_cancelling_a_paid_order_returns_the_stock():
    order = data.create_order("prensa-francesa", 2)
    data.pay(order["token"])

    data.cancel_order(order["number"])

    assert data.PRODUCTS["prensa-francesa"]["stock"] == 4


def test_store_texts_are_cited_by_file_and_paragraph():
    sources = [
        piece["source"]
        for piece in call("search_docs", {"question": "Posso trocar a cafeteira?"})
    ]

    assert "trocas.md §1" in sources


def test_what_the_store_never_wrote_is_not_found():
    assert call("search_docs", {"question": "Vocês aceitam pix?"}) == []
