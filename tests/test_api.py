from fastapi.testclient import TestClient

from assistant.app.limits import RateLimit
from assistant.app.main import create_app
from assistant.store import data

from .conftest import ScriptedModel, assistant_with, turn


def client(*turns, max_messages=10):
    app = create_app(assistant_with(ScriptedModel(*turns)), RateLimit(max_messages, 3600))
    return TestClient(app)


def event_names(body):
    return [
        line.removeprefix("event: ") for line in body.splitlines() if line.startswith("event: ")
    ]


def test_chat_answers_in_sse():
    response = client(turn("Oi!")).post("/api/chat", json={"message": "oi"})

    assert response.headers["content-type"].startswith("text/event-stream")
    assert event_names(response.text) == ["conversation", "text", "suggestions", "end"]


def test_empty_or_huge_message_is_refused():
    c = client()

    assert c.post("/api/chat", json={"message": ""}).status_code == 422
    assert c.post("/api/chat", json={"message": "x" * 2001}).status_code == 422
    assert c.post("/api/chat", content="não é json").status_code == 400


def test_message_limit_per_visitor():
    c = client(turn("1"), turn("2"), max_messages=2)

    codes = [c.post("/api/chat", json={"message": "oi"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_opening_the_link_does_not_pay_only_clicking_pay_does():
    c = client()
    order = data.create_order("prensa-francesa", 1)

    page = c.get(f"/checkout/{order['token']}")
    assert "Pagar R$ 149,00" in page.text
    assert data.order_status(order["number"])["status"] == "aguardando pagamento"

    paid = c.post(f"/checkout/{order['token']}/pay")
    assert "pago" in paid.text
    assert data.order_status(order["number"])["status"] == "pago"


def test_a_made_up_link_is_404():
    assert client().get("/checkout/made-up").status_code == 404


def test_confirming_in_an_unknown_conversation_is_404():
    response = client().post(
        "/api/confirm", json={"conversation": "nope", "id": "x", "allow": True}
    )

    assert response.status_code == 404


def test_the_shop_lists_products_and_the_page_loads():
    c = client()

    assert len(c.get("/api/products").json()) == 4
    assert "Loja Exemplo" in c.get("/").text
