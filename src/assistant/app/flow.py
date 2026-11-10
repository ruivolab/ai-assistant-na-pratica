"""Voz: quais próximas perguntas sugerir.

O fluxo decide os caminhos abertos, e cada botão bate numa ferramenta que existe.
"""

TALK_TO_A_PERSON = "Falar com uma pessoa"

ACTIONS = {
    "Ver os produtos": "list_products",
    "Ver parecidos com estoque": "list_products",
    "Ver detalhes": "product_details",
    "Quero comprar": "create_purchase_link",
    "Como está meu pedido": "order_status",
    TALK_TO_A_PERSON: "hand_off_to_person",
}


def tool_for(suggestion):
    for start, tool in ACTIONS.items():
        if suggestion.startswith(start):
            return tool
    return None


def suggestion_after(tool, result):
    if tool in ("list_products", "search_products"):
        if isinstance(result, list) and result:
            return f"Ver detalhes: {result[0]['name']}"
        return None
    if not isinstance(result, dict):  # a ferramenta falhou: nada a sugerir a partir dela
        return None
    if tool == "create_purchase_link" and result.get("created"):
        return f"Como está meu pedido {result['number']}?"
    if tool == "product_details" and result.get("found", True):
        if result.get("available"):
            return f"Quero comprar: {result['name']}"
        return f"Ver parecidos com estoque ({result['category']})"
    return None


def suggestions(used_tools):
    options = []
    for tool, result in reversed(used_tools):  # o que aconteceu por último vem primeiro
        option = suggestion_after(tool, result)
        if option and option not in options:
            options.append(option)
    if not options:
        options = ["Ver os produtos", "Como está meu pedido?"]
    return [*options[:2], TALK_TO_A_PERSON]
