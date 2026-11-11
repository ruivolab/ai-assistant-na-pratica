# Loja Exemplo · Passo 12

O código do livro **AI Assistant na Prática**, do jeito que ele fica no fim do Passo 12.
Cada passo do livro tem uma tag (`passo-01` a `passo-12`). O código completo, organizado em pacote, está
no branch `main` e no anexo do livro.

```bash
uv sync
export ANTHROPIC_API_KEY=...   # a sua chave
uv run uvicorn main:app --reload
```
