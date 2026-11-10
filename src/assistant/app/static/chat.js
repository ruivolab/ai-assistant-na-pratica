const money = (v) => (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

// O balão: manda a pergunta para o NOSSO servidor e lê a resposta em SSE, pedaço por pedaço.
function chat() {
  return {
    open: false,
    text: "",
    sending: false,
    conversation: null,
    messages: [{ from: "assistant", text: "Oi! Posso ajudar a escolher um produto ou ver um pedido." }],
    suggestions: ["Ver os produtos", "Como está meu pedido?", "Falar com uma pessoa"],

    async send(text) {
      text = (text || "").trim();
      if (!text || this.sending) return;
      this.text = "";
      this.suggestions = [];
      this.sending = true;
      this.messages.push({ from: "customer", text });
      let current = { from: "assistant", text: "" };
      this.messages.push(current);

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ conversation: this.conversation, message: text }),
        });
        if (!response.ok) {
          current.text = response.status === 429
            ? "Muitas mensagens por agora. Tente mais tarde."
            : "Não consegui responder.";
          return;
        }
        await readEvents(response.body, (kind, payload) => {
          if (kind === "conversation") this.conversation = payload.id;
          else if (kind === "text") current.text += payload;
          else if (kind === "confirm") this.messages.push({ from: "assistant", confirm: payload });
          else if (kind === "link") this.messages.push({ from: "assistant", link: payload });
          else if (kind === "handoff") this.notice("Uma pessoa do atendimento vai continuar daqui.");
          else if (kind === "suggestions") this.suggestions = payload;
          else if (kind === "blocked" || kind === "error") current.text = payload;

          // um cartão entrou no meio: o texto seguinte vai num balão novo
          if (current.text && this.messages.at(-1) !== current) {
            current = { from: "assistant", text: "" };
            this.messages.push(current);
          }
          this.$nextTick(() => (this.$refs.list.scrollTop = this.$refs.list.scrollHeight));
        });
      } finally {
        this.messages = this.messages.filter((m) => m.text || m.confirm || m.link);
        this.sending = false;
      }
    },

    notice(text) {
      this.messages.push({ from: "notice", text });
    },

    async decide(message, allow) {
      message.decided = true;
      const response = await fetch("/api/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation: this.conversation, id: message.confirm.id, allow }),
      });
      const r = await response.json();
      if (!r.ok) return this.notice(r.reason || "Não deu certo.");
      if (!r.done) return this.notice("Tudo certo, nada mudou.");
      if (r.result?.cancelled) return this.notice(`Pedido ${r.result.number} cancelado.`);
      this.notice(r.result?.reason || "Feito.");
    },
  };
}

// Lê um fluxo SSE: blocos "event: tipo" + "data: json", separados por uma linha em branco.
async function readEvents(body, onEvent) {
  const reader = body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let end;
    while ((end = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      const kind = /^event: (.*)$/m.exec(block)?.[1];
      const payload = /^data: (.*)$/m.exec(block)?.[1];
      if (kind && payload !== undefined) onEvent(kind, JSON.parse(payload));
    }
  }
}
