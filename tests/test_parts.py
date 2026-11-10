import asyncio

import pytest
from fastmcp import Client

from assistant.app import flow
from assistant.app.conversation import APP_TOOLS
from assistant.app.limits import CanaryGuard, RateLimit
from assistant.app.skills import catalog, load
from assistant.store.server import mcp

from .paths import SKILLS


def test_the_book_skills_load_with_name_and_description():
    skills = load(SKILLS)

    assert sorted(skills) == ["close-purchase", "product-questions"]
    assert "Não use para" in skills["close-purchase"].description
    assert "create_purchase_link" in skills["close-purchase"].steps
    assert catalog(skills).count("\n") == 1


def test_a_skill_without_header_is_refused(tmp_path):
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "SKILL.md").write_text("só texto", encoding="utf-8")

    with pytest.raises(ValueError, match="cabeçalho"):
        load(tmp_path)


def existing_tools():
    async def names():
        async with Client(mcp) as client:
            return {tool.name for tool in await client.list_tools()}

    return asyncio.run(names()) | {tool["name"] for tool in APP_TOOLS}


SCENARIOS = [
    [],
    [
        (
            "list_products",
            [{"id": "prensa-francesa", "name": "Prensa francesa 1 L", "price": 149.0}],
        )
    ],
    [("product_details", {"name": "Prensa", "category": "cafeteiras", "available": True})],
    [("product_details", {"name": "Moedor", "category": "moedores", "available": False})],
    [("create_purchase_link", {"created": True, "number": 1001})],
    [("list_products", {"error": "falhou"})],
]


@pytest.mark.parametrize("used_tools", SCENARIOS)
def test_every_suggestion_maps_to_a_tool_that_exists(used_tools):
    suggestions = flow.suggestions(used_tools)

    assert 1 < len(suggestions) <= 3
    assert suggestions[-1] == flow.TALK_TO_A_PERSON
    assert all(flow.tool_for(s) in existing_tools() for s in suggestions)


def test_after_details_suggest_buying_and_when_sold_out_suggest_similar():
    assert flow.suggestions(SCENARIOS[2])[0] == "Quero comprar: Prensa"
    assert flow.suggestions(SCENARIOS[3])[0] == "Ver parecidos com estoque (moedores)"


def test_the_canary_never_leaks_even_split_across_pieces():
    guard = CanaryGuard("CANARIO-abc")
    out = "".join(guard.filter(p) for p in ["Olá, o có", "digo é CANA", "RIO-a", "bc, viu?"])

    assert guard.leaked is True
    assert "CANA" not in out + guard.finish()


def test_normal_text_comes_out_whole():
    guard = CanaryGuard("CANARIO-abc")
    out = "".join(guard.filter(p) for p in ["A prensa ", "custa R$ 149."]) + guard.finish()

    assert out == "A prensa custa R$ 149."


def test_rate_limit_per_visitor():
    now = [0.0]
    limit = RateLimit(max_messages=2, window_seconds=60, clock=lambda: now[0])

    assert [limit.allow("a"), limit.allow("a"), limit.allow("a"), limit.allow("b")] == [
        True,
        True,
        False,
        True,
    ]
    now[0] = 61
    assert limit.allow("a") is True
