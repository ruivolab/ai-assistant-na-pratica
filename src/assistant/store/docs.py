"""Os textos da loja (trocas, frete, manuais), cortados em pedaços com endereço.

A busca é por palavras: sem banco e sem embeddings. O volume 2 troca por busca por significado.
"""

import re
import unicodedata
from pathlib import Path


def load_pieces(folder: Path):
    pieces = []
    for path in sorted(folder.glob("*.md")):
        texts = path.read_text(encoding="utf-8").split("\n\n")
        for number, text in enumerate(texts, 1):
            if text.strip():
                pieces.append({"source": f"{path.name} §{number}", "text": text.strip()})
    return pieces


def roots(text):
    # sem acento, minúsculo e só o começo das palavras de 4 letras ou mais:
    # trocar, troca e trocas viram "troca"
    plain = unicodedata.normalize("NFKD", text.lower())
    plain = plain.encode("ascii", "ignore").decode()
    return {word[:5] for word in re.findall(r"\w{4,}", plain)}


def search(pieces, question, limit=3):
    wanted = roots(question)
    found = []
    for piece in pieces:
        score = len(wanted & roots(piece["text"]))
        if score > 0:
            found.append((score, piece))
    found.sort(key=lambda pair: pair[0], reverse=True)
    return [piece for _, piece in found[:limit]]
