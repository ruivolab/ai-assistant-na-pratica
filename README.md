# AI Assistant na Prática: o código do livro

O assistente da **Loja Exemplo**, uma loja de café de mentira. O cliente vê os produtos, tira dúvidas no balão, pede o
link de compra e paga na página do link (o pagamento é simulado).

## As peças, no código

| Parte do livro | Onde está |
|---|---|
| O caminho de uma pergunta | `src/assistant/app/main.py`: o servidor que o balão chama (`POST /api/chat`, resposta em SSE) |
| A cabeça | `src/assistant/app/model.py`: a chamada à API da Anthropic, em streaming |
| Voz | `conversation.py` (as instruções e o laço) e `flow.py` (as próximas perguntas sugeridas) |
| Skills | `skills/*/SKILL.md` e `src/assistant/app/skills.py` (carregar é ler um arquivo: sem LangChain) |
| Mãos | `src/assistant/store/server.py`: o servidor MCP, feito com FastMCP |
| Memória | `docs/*.md` (os textos da loja) e `store/docs.py` (pedaços com endereço e busca por palavras) |
| Limites | `store/rules.py` (read, prepare ou change; change pede o sim da pessoa) e `app/limits.py` (canário, teto de uso) |
| O balão | `src/assistant/app/static/`: HTML + Alpine.js, sem build |

Três regras que o código segue e os testes conferem:

1. **A IA prepara, a pessoa decide.** O link de compra não cobra nada. Só o clique em "Pagar", na página do link, paga.
   Abrir o link também não paga (`test_opening_the_link_does_not_pay_only_clicking_pay_does`).
2. **O sim é de uma pessoa.** Cancelar um pedido mostra um botão Permitir/Recusar na tela. A IA não tem como clicar
   (`test_the_ai_cannot_confirm_on_its_own`).
3. **O balão só conversa com o seu servidor.** A chave da API fica no servidor, nunca no navegador.

## Passo a passo

Cada passo do livro tem uma tag com o projeto do jeito que ele fica no fim daquele passo, no branch
`passos`: `passo-01` (o servidor que responde ok) até `passo-12` (Docker e a VPS). Os passos usam um
`main.py` só; este `main` é o código completo do anexo, organizado em pacote.

```bash
git clone https://github.com/ruivolab/ai-assistant-na-pratica.git
cd ai-assistant-na-pratica
git checkout passo-07     # o projeto no fim do Passo 7
```

## Rodar

Você precisa de Python 3.12 ou mais novo, do [uv](https://docs.astral.sh/uv/) e de uma chave da API da Anthropic
(console.anthropic.com). Cada mensagem custa frações de centavo; o teto padrão é 30 mensagens por hora por visitante.

```bash
uv sync
uv run pytest                      # 40 testes, sem chamar a API
cp .env.example .env               # e cole a sua ANTHROPIC_API_KEY
set -a; source .env; set +a
uv run uvicorn assistant.app.main:app --reload
```

Abra http://localhost:8000 e clique no balão.

### Com Docker

```bash
cp .env.example .env               # e cole a sua ANTHROPIC_API_KEY
docker compose up --build
```

### No Claude Desktop (só as mãos)

O mesmo servidor MCP roda sozinho: `uv run store-mcp`. Veja o capítulo Mãos.

### Como MCP remoto (a demo pública)

`src/assistant/remote.py` serve as mesmas ferramentas por HTTP, em `/mcp`, para qualquer pessoa ligar no Claude
dela. Quem pensa é o Claude do visitante, então o servidor não gasta API e o balão fica desligado. O checkout continua
no mesmo servidor: a IA cria o link e a pessoa paga com o clique.

```bash
STORE_PUBLIC_URL=http://localhost:8000 uv run uvicorn assistant.remote:app --factory
```

- Cada sessão MCP (protocolo com aperto de mão) tem a própria loja. No protocolo 2026-07-28 sem login, nada identifica
  o visitante de uma chamada para a outra: ele divide uma loja com os outros, que recomeça do zero a cada hora. Nela,
  o número do pedido é sorteado (de 100000 a 999999), para não dizer quantos pediram nem abrir o pedido do outro.
- O catálogo da demo é em inglês (`DEMO_PRODUCTS`, em `remote.py`), e o produto sem estoque vem com um aviso para a IA
  não oferecê-lo. O app do livro segue com o catálogo em português.
- Teto de chamadas por endereço: `MCP_CALLS_PER_HOUR` (padrão 300).

## Pôr no ar

Uma VPS com Docker basta. Passo a passo em [DEPLOY.md](DEPLOY.md).

## O que este exemplo não faz

- Guarda tudo em memória: reiniciou, zerou. Num produto de verdade, use um banco.
- O pagamento é de mentira. Num produto de verdade, o botão "Pagar" leva ao checkout do seu meio de pagamento, e
  quem marca o pedido como pago é o aviso (webhook) dele, nunca o chat.
- Não tem login. Qualquer pessoa com o link de compra vê aquele pedido (o link é longo e aleatório).
