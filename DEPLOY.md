# Pôr no ar numa VPS

Serve qualquer VPS Linux com 1 GB de RAM ou mais (Hostinger, DigitalOcean, Hetzner, Contabo...). O exemplo usa
Ubuntu 24.04.

## 1. O domínio

No painel do seu domínio, crie um registro **A** apontando `loja.seudominio.com.br` para o IP da VPS. Espere ele
responder: `ping loja.seudominio.com.br` tem que mostrar o IP da VPS.

## 2. A VPS

```bash
ssh root@IP-DA-VPS
curl -fsSL https://get.docker.com | sh     # instala Docker e o plugin compose
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
```

## 3. O código e a chave

```bash
git clone https://github.com/ruivolab/ai-assistant-na-pratica.git
cd ai-assistant-na-pratica
cp .env.example .env
nano .env        # cole a ANTHROPIC_API_KEY e ponha o seu DOMAIN
chmod 600 .env
```

A chave fica só neste arquivo, na VPS. Nunca no git, nunca no navegador.

## 4. Subir

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
docker compose -f compose.yaml -f compose.prod.yaml logs -f caddy    # espere o certificado sair
```

Abra `https://loja.seudominio.com.br`. O Caddy tira e renova o certificado HTTPS sozinho.

## 5. Atualizar

```bash
git pull
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
```

## Antes de abrir para o público

- **Ponha um limite de gasto** na sua conta da API (console.anthropic.com → Limits). O teto por visitante
  (`ASSISTANT_MESSAGES_PER_HOUR`) segura uma pessoa, não um ataque com muitos IPs.
- **Só o Caddy fala com a internet**: no `compose.prod.yaml` o app não publica porta nenhuma.
- **Passe o checklist do livro** (capítulo Fechamento).
