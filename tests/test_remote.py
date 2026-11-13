import socket
import threading
import time

import httpx
import pytest
import uvicorn
from fastmcp import Client

from assistant.app.limits import RateLimit
from assistant.remote import SHARED_STORE_SECONDS, Visitors, create_remote_app


@pytest.fixture
def anyio_backend():
    return "asyncio"


TOOLS = {
    "list_products",
    "search_products",
    "product_details",
    "order_status",
    "search_docs",
    "create_purchase_link",
    "cancel_order",
}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def serve():
    servers = []

    def start(**kwargs):
        port = free_port()
        app = create_remote_app(public_url=f"http://127.0.0.1:{port}", **kwargs)
        server = uvicorn.Server(uvicorn.Config(app, port=port, log_level="warning"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        while not server.started:
            time.sleep(0.02)
        servers.append((server, thread))
        return f"http://127.0.0.1:{port}"

    yield start
    for server, thread in servers:
        server.should_exit = True
        thread.join(5)


def buy(client):
    return client.call_tool("create_purchase_link", {"product_id": "prensa-francesa"})


def result(call):
    return call.structured_content.get("result", call.structured_content)


@pytest.mark.anyio
async def test_the_store_tools_answer_over_http(serve):
    base = serve()

    async with Client(f"{base}/mcp") as client:
        tools = {tool.name for tool in await client.list_tools()}
        products = result(await client.call_tool("list_products", {}))

    assert tools == TOOLS
    assert {p["id"] for p in products} >= {"cafeteira-italiana", "prensa-francesa"}


def legacy(base):
    # o protocolo com aperto de mão, que guarda a sessão de uma chamada para a outra
    return Client(f"{base}/mcp", mode="legacy")


@pytest.mark.anyio
async def test_each_visitor_with_a_session_gets_their_own_store(serve):
    base = serve()

    async with legacy(base) as ana, legacy(base) as bia:
        link = result(await buy(ana))
        seen_by_bia = result(await bia.call_tool("order_status", {"number": link["number"]}))
        seen_by_ana = result(await ana.call_tool("order_status", {"number": link["number"]}))

    assert seen_by_bia == {"number": link["number"], "found": False}
    assert seen_by_ana["status"] == "aguardando pagamento"


@pytest.mark.anyio
@pytest.mark.parametrize("protocol", ["legacy", "2026-07-28"])
async def test_only_the_click_on_the_link_pays(serve, protocol):
    base = serve()
    client = legacy(base) if protocol == "legacy" else Client(f"{base}/mcp")

    async with client:
        link = result(await buy(client))
        assert link["link"].startswith(f"{base}/checkout/")

        page = httpx.get(link["link"])
        assert "Pagar R$ 149,00" in page.text
        before = result(await client.call_tool("order_status", {"number": link["number"]}))

        httpx.post(f"{link['link']}/pay")
        after = result(await client.call_tool("order_status", {"number": link["number"]}))

    assert before["status"] == "aguardando pagamento"
    assert after["status"] == "pago"


@pytest.mark.anyio
async def test_cancelling_without_a_person_to_say_yes_changes_nothing(serve):
    base = serve()

    async with legacy(base) as client:
        link = result(await buy(client))
        answer = result(await client.call_tool("cancel_order", {"number": link["number"]}))
        status = result(await client.call_tool("order_status", {"number": link["number"]}))

    assert answer["done"] is False
    assert status["status"] == "aguardando pagamento"


def test_too_many_calls_from_one_address_get_429(serve):
    base = serve(rate_limit=RateLimit(max_messages=3, window_seconds=3600))
    ping = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
    headers = {"Accept": "application/json, text/event-stream"}

    codes = [httpx.post(f"{base}/mcp", json=ping, headers=headers).status_code for _ in "1234"]

    assert codes[3] == 429
    assert 429 not in codes[:3]


def test_the_chat_balloon_is_off_in_the_public_demo(serve):
    base = serve()

    response = httpx.post(f"{base}/api/chat", json={"message": "oi"})

    assert response.status_code == 503
    assert httpx.get(f"{base}/health").json() == {"status": "ok"}


def test_visitors_without_a_session_share_a_store_that_starts_over_every_hour():
    now = [0.0]
    visitors = Visitors(clock=lambda: now[0])

    first = visitors.store_for(None)
    assert visitors.store_for(None) is first

    now[0] = SHARED_STORE_SECONDS + 1
    assert visitors.store_for(None) is not first


def test_the_oldest_visitor_is_forgotten_past_the_limit():
    visitors = Visitors(max_visitors=2)

    ana = visitors.store_for("ana")
    visitors.store_for("bia")
    visitors.store_for("caio")

    assert visitors.store_for("ana") is not ana


@pytest.mark.anyio
async def test_the_demo_catalog_speaks_english_and_skips_empty_fields(serve):
    base = serve()

    async with Client(f"{base}/mcp") as client:
        products = result(await client.call_tool("list_products", {}))
        coffee = result(
            await client.call_tool("product_details", {"product_id": "cafe-especial-250g"})
        )

    assert {p["name"] for p in products} >= {
        "Specialty coffee 250 g (whole beans)",
        "French press 1 L",
    }
    assert "warranty" not in coffee
    assert "Minas Gerais" in coffee["description"]


@pytest.mark.anyio
async def test_a_sold_out_product_says_not_to_offer_it(serve):
    base = serve()

    async with Client(f"{base}/mcp") as client:
        listed = {p["id"]: p for p in result(await client.call_tool("list_products", {}))}
        grinder = result(
            await client.call_tool("product_details", {"product_id": "moedor-manual"})
        )

    assert "do not offer" in listed["moedor-manual"]["note"]
    assert "do not offer" in grinder["note"]
    assert "note" not in listed["cafe-especial-250g"]


@pytest.mark.anyio
async def test_in_the_shared_store_order_numbers_reveal_nothing(serve):
    base = serve()

    async with Client(f"{base}/mcp") as ana, Client(f"{base}/mcp") as bia:
        first = result(await buy(ana))
        second = result(await buy(ana))
        guesses = [
            result(await bia.call_tool("order_status", {"number": n})) for n in (1001, 1002)
        ]
        mine = result(await ana.call_tool("order_status", {"number": second["number"]}))

    assert all(100_000 <= o["number"] <= 999_999 for o in (first, second))
    assert second["number"] != first["number"] + 1
    assert all(g["found"] is False for g in guesses)
    assert mine["status"] == "aguardando pagamento"
