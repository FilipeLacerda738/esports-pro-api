# Configuração de segurança

## Migração deste endurecimento

1. Instale `requirements.txt`. Foram atualizados AnyIO, Starlette e pydantic-settings
   para corrigir os alertas encontrados na auditoria de dependências.
2. Defina `ENVIRONMENT=production` explicitamente. Valores ausentes ou desconhecidos
   impedem a inicialização. `.env.example` serve apenas para desenvolvimento local.
3. Gere duas chaves diferentes com `python -c "import secrets; print(secrets.token_urlsafe(48))"`:
   `API_ACCESS_KEY` para leitura pelo aplicativo e `SECRET_KEY` exclusivamente no servidor.
   Nunca distribua `SECRET_KEY` no APK. Substitua a antiga chave compartilhada no servidor
   e no aplicativo de forma coordenada. Alterar `SECRET_KEY` invalida todos os JWTs existentes.
4. Configure `DATABASE_SSL=true` e a URL do PostgreSQL. O cliente verifica certificado e
   hostname; caso necessário, indique a CA do provedor em `DATABASE_CA_FILE`.
   Parâmetros como `sslmode=disable` na URL não desabilitam essa proteção. As migrações
   Alembic usam a mesma política. TLS só pode ser desabilitado para loopback em desenvolvimento/testes.
5. O worker único atual pode manter `RATE_LIMIT_STORAGE_URI=memory://`, sem exigir uma nova
   credencial no deploy. Antes de escalar para múltiplos processos/réplicas, configure
   `rediss://usuario:senha@host:porta/0` para que todos compartilhem os mesmos limites.
   Certificado e hostname do Redis remoto são verificados. Redis indisponível impede o startup
   ou retorna `503` nas requisições.
6. Para clientes web, liste origens HTTPS exatas em `BACKEND_CORS_ORIGINS`, por exemplo
   `["https://app.example.com"]`. Para apenas Android, mantenha `[]`. Não são usados cookies
   de autenticação nem `Access-Control-Allow-Credentials`. CORS não autentica clientes.
7. Execute a API atrás de HTTPS. Configure no proxy limite de corpo de 16 KiB e tempos de
   leitura/conexão. No Uvicorn, confie em cabeçalhos de encaminhamento somente dos IPs do
   proxy real (`--forwarded-allow-ips`); nunca use `*` em uma API diretamente acessível.
   Sem proxy, use `--no-proxy-headers`. Restrinja o acesso direto ao backend por firewall.

## Alterações de contrato

- `POST /api/v1/teams/`, `POST /api/v1/matches/sync-now` e todas as rotas `/api/v1/test/*`
  foram removidas. Nenhuma chave de aplicativo ou conta de usuário permite essas operações.
  Times e partidas continuam sendo atualizados pelo agendador. Não existe papel administrativo
  público nem mecanismo de promoção de usuários.
- `GET /api/v1/teams/` preserva o formato e o comportamento usado pelo Android: sem parâmetros,
  retorna todos os times. Paginação opcional está disponível com `page` e `limit` (máximo 100).
- `/api/v1/auth/register`, `/login`, `/me` e `/profile/team` estão registrados.
  O cadastro preserva senhas de 6 a 72 caracteres; hashes existentes continuam compatíveis.
  Login usa formulário OAuth2 (`username`, `password`), e `/me` e atualização de perfil exigem
  `Authorization: Bearer <token>`. O padrão de sete dias foi preservado (configurável),
  e tokens emitidos pela versão anterior continuam aceitos até expirarem. Novos tokens incluem
  assinatura, emissor, audiência e campos temporais obrigatórios. Sem refresh token:
  ao expirar, o cliente precisa autenticar novamente.
- Limites: 120 requisições/minuto por IP, 10/minuto por IP compartilhadas entre cadastro e login,
  5 tentativas/minuto por conta no login, 120/minuto por usuário autenticado.
  Email e username de uma conta compartilham o limite. Respostas `429` incluem `Retry-After`.
- Corpos maiores que 16 KiB retornam `413`, inclusive com transferência em blocos.
  O tempo total de leitura do corpo é limitado a 10 segundos.
- `/api/v1/system/app-version` tem cache de 5 minutos por processo, deduplicação de requisições
  simultâneas e cache de falha por 1 minuto, preservando o último resultado válido.
- Swagger/OpenAPI só ficam disponíveis em desenvolvimento explícito.
- Docker publica o PostgreSQL apenas em `127.0.0.1:5432`. Use senha própria e forte.

O agendador atual está embutido no processo da API: use **um worker** até separar os jobs
em um serviço dedicado, para evitar sincronizações duplicadas. As cotas Redis já são compartilhadas.
Credenciais de deploy, firewall e serviços externos não são modificados pela alteração de código.

## Verificação

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m pip check
python -m pip_audit -r requirements.txt
```

Os testes usam credenciais fictícias, banco SQLite temporário e servidores TLS locais; não
inicializam jobs, consultam a PandaScore ou alteram dados de produção. O teste TLS verifica CA
não confiável, hostname incorreto e conexão válida. Uma auditoria sem alertas não garante
ausência de vulnerabilidades futuras. Repita a auditoria ao atualizar dependências.

## English deployment notes

Set `ENVIRONMENT=production`, keep `SECRET_KEY` server-only, and enable verified PostgreSQL TLS.
The current single worker may use the in-memory rate limiter; configure shared Redis with
`RATE_LIMIT_STORAGE_URI=rediss://...` before scaling horizontally. Remote Redis certificates and hostnames are verified.
Configure exact HTTPS CORS origins, or `[]` for Android-only clients. Rotate the old mobile key
in coordination with the Android release; rotating the JWT key invalidates existing sessions.
Keep one API worker while the scheduler is embedded. Terminate HTTPS at a trusted proxy and
trust forwarded headers only from that proxy's addresses.

Public team creation, manual sync and diagnostic routes were removed; scheduled imports remain.
Team pagination is optional; an unparameterized request still returns the complete list for Android
compatibility. Authentication is enabled, legacy sessions remain valid until expiration, and existing
password hashes remain supported. Install `requirements-dev.txt` to run tests.
