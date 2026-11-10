"""Os três tipos de ferramenta. O tipo diz quem precisa dizer sim.

- read: só consulta. Passa direto.
- prepare: deixa algo pronto que a pessoa aprova em outro lugar
  (o link de compra: só o botão "Pagar" paga).
- change: muda algo de verdade. A ferramenta pergunta à PESSOA, não ao modelo.
"""

from fastmcp import Client, Context, FastMCP

READ = {"annotations": {"readOnlyHint": True}, "meta": {"kind": "read"}}
PREPARE = {
    "annotations": {"readOnlyHint": False, "destructiveHint": False},
    "meta": {"kind": "prepare"},
}
CHANGE = {
    "annotations": {"readOnlyHint": False, "destructiveHint": True},
    "meta": {"kind": "change"},
}


def kind_of(tool):
    kind = (tool.meta or {}).get("kind")
    if kind in ("read", "prepare"):
        return kind
    return "change"  # sem tipo, ou tipo desconhecido: na dúvida, pede o sim


async def person_said_yes(ctx: Context, question):
    # A pergunta vai para o app (o Claude Desktop, ou o nosso balão), que mostra para a pessoa.
    # O modelo não vê essa pergunta e não tem como responder por ela.
    try:
        answer = await ctx.elicit(question, response_type=bool)
    except Exception:
        return False  # o app não sabe perguntar: sem pergunta, sem sim
    return answer.action == "accept" and answer.data is True


async def tools_without_kind(mcp: FastMCP):
    async with Client(mcp) as client:
        tools = await client.list_tools()
    return sorted(tool.name for tool in tools if (tool.meta or {}).get("kind") is None)
