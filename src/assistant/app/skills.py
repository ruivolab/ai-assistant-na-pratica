"""Skills: receitas em texto.

Só o nome e a descrição vão sempre para o modelo; o passo a passo, quando ele pede.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Skill:
    name: str
    description: str
    steps: str


def load(folder: Path):
    skills = {}
    for file in sorted(folder.glob("*/SKILL.md")):
        text = file.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise ValueError(f"{file}: falta o cabeçalho com name e description")
        _, header, body = text.split("---", 2)
        meta = yaml.safe_load(header)
        skills[meta["name"]] = Skill(meta["name"], meta["description"], body.strip())
    return skills


def catalog(skills):
    return "\n".join(f"- {skill.name}: {skill.description}" for skill in skills.values())
