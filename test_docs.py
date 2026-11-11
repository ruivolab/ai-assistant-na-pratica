from store.server import search_docs


def sources(question):
    return [piece["source"] for piece in search_docs(question)]


def test_brings_the_piece_that_answers():
    assert "trocas.md §1" in sources("Posso trocar a cafeteira?")
    assert "frete.md §2" in sources(
        "Quanto tempo o frete leva para o Norte?")


def test_brings_nothing_when_the_store_never_wrote_it():
    assert sources("Vocês aceitam pix?") == []
