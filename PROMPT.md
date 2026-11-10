Monte comigo um assistente de IA para uma loja virtual. Vá em passos pequenos e me explique cada arquivo.

O produto
- Uma loja de café de exemplo com 4 produtos, catálogo e pedidos guardados em memória.
- No canto da página, um balão de chat. O cliente vê produtos, tira dúvidas, pede o link de compra
  e paga na página do link (pagamento simulado).

A pilha (não troque)
- Python 3.12+ com uv. FastAPI no servidor. A API da Anthropic direto, com streaming.
- Um servidor MCP com FastMCP para as ferramentas da loja, usado no mesmo processo.
- Front em HTML + Alpine.js, sem build. Docker e docker compose. Sem LangChain, sem pydantic
  no nosso código, sem framework de agente. Código simples, nomes em inglês, comentários em português.

As regras (são o coração do projeto)
1. Toda ferramenta tem um tipo: read (só consulta), prepare (deixa algo pronto que a pessoa aprova
   em outro lugar) ou change (muda algo). Sem tipo conta como change.
2. change pergunta à PESSOA por elicitation do MCP; o modelo nunca confirma sozinho.
   No chat, isso vira um botão Permitir/Recusar, com um código que vale uma vez só.
3. O link de compra é prepare: não cobra nada. Abrir o link (GET) só mostra o pedido;
   só o botão "Pagar" (POST) paga. Pagar nunca é uma ferramenta da IA.
4. As skills são arquivos skills/<nome>/SKILL.md. Só nome e descrição vão para o modelo;
   o passo a passo ele abre com uma ferramenta open_skill.
5. Uma palavra-canário nas instruções; se ela aparecer numa resposta, bloqueie a resposta.
6. Teto de mensagens por visitante e mensagem de 1 a 2000 caracteres.
7. Depois de cada resposta, sugira até 2 próximas perguntas que batam em ferramentas que existem,
   mais "Falar com uma pessoa" (uma ferramenta que passa o caso com um resumo).
8. Os textos da loja (trocas, frete, manuais) ficam em docs/*.md, cortados por parágrafo, cada pedaço
   com a fonte (arquivo §n). Uma ferramenta search_docs busca por palavras, sem banco; a IA responde
   só com o trecho, cita a fonte e, sem trecho, diz que não encontrou.
9. A chave da API fica só no servidor. O navegador fala só com o nosso servidor, em SSE.

Ferramentas da loja: list_products, search_products, product_details, order_status, search_docs (read);
create_purchase_link (prepare); cancel_order (change).

Testes primeiro: para cada regra acima, um teste que falha antes do código. Os testes não
chamam a API (use um modelo de mentira que devolve respostas roteirizadas).
