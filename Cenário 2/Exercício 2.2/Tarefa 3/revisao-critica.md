# Revisão Crítica do Código Gerado pelo Copilot
---

## Problema 1 — `OPTIONS` rejeitado com 405, quebrando preflight de CORS

### Código original

```ts
if (request.method !== "POST") {
  return {
    status: 405,
    jsonBody: { error: "Method Not Allowed" }
  };
}
```

O binding do `app.http` incluía `OPTIONS` na lista de métodos aceitos, mas o handler devolvia `405` para qualquer método diferente de `POST` — incluindo o próprio `OPTIONS`.

O Anexo C define que este projeto terá um painel web em React consumindo esta mesma API. Navegadores disparam automaticamente uma requisição `OPTIONS` de *preflight* antes de um `POST` que envie `Content-Type: application/json`, esperando uma resposta de sucesso com headers de CORS. Um `405` nesse preflight bloqueia a chamada real antes mesmo dela ser enviada — o painel web nunca conseguiria consumir o endpoint.

### Correção aplicada

```ts
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type"
};

if (request.method === "OPTIONS") {
  return { status: 200, headers: corsHeaders };
}
```

### Problema secundário descoberto durante a correção

A primeira correção aplicou os `corsHeaders` **apenas** na resposta do `OPTIONS`, deixando as demais respostas (200, 400, 405) sem o header `Access-Control-Allow-Origin`. Isso só é perceptível testando uma chamada real de navegador — ferramentas como `curl`/Postman não aplicam política de CORS, então o problema passaria despercebido em testes manuais simples.

**Correção final:** função auxiliar `withCors()` envolvendo todas as respostas do handler:

```ts
function withCors(response: HttpResponseInit): HttpResponseInit {
  return {
    ...response,
    headers: { ...corsHeaders, ...(response.headers ?? {}) }
  };
}
```

Todas as respostas (`OPTIONS`, `405`, `400` malformado, `400` de validação, `200`) passaram a usar `withCors(...)`.

### Verificação real

```
curl.exe -i -X POST http://localhost:7071/api/query -H "Content-Type: application/json" -d '{"question":"teste"}'

HTTP/1.1 200 OK
Access-Control-Allow-Headers: Content-Type
Access-Control-Allow-Methods: POST, OPTIONS
Access-Control-Allow-Origin: *
{"received":true}
```

O header `Access-Control-Allow-Origin: *` confirmado presente numa resposta de sucesso (`200`), não apenas no preflight.

---

## Problema 2 — Erro de parsing de JSON descartado silenciosamente

### Código original

```ts
let body: unknown;
try {
  body = await request.json();
} catch {
  body = undefined;
}
```

Um JSON malformado no corpo da requisição fazia a exceção de parsing ser descartada sem log, com o fluxo caindo na validação genérica do Zod — que retornava uma mensagem enganosa ("campo `question` obrigatório") quando o problema real era o corpo não poder ser interpretado como JSON.

Consumidores da API perderiam tempo depurando "por que `question` não está chegando" quando o problema é um JSON malformado antes mesmo de chegar à validação de schema. Além disso, um erro de parsing é informação operacional relevante que deveria ser logada — o padrão de logging estruturado do projeto (pino) exige isso.

### Correção aplicada

```ts
try {
  body = await request.json();
} catch (error) {
  logger.warn(
    { method: request.method, path: request.url, error },
    "malformed JSON body"
  );

  return withCors({
    status: 400,
    jsonBody: { error: "Malformed JSON body" }
  });
}
```

### Verificação real

```
curl -i -X POST http://localhost:7071/api/query -H "Content-Type: application/json" -d "{\"question\": \"tes..." (JSON truncado)

HTTP/1.1 400 Bad Request
Access-Control-Allow-Origin: *
{"error":"Malformed JSON body"}
```

Mensagem específica e distinta do erro genérico de validação Zod, confirmando o comportamento esperado.

---

## Observações adicionais (não classificadas como bugs)

| Observação | Classificação | Ação recomendada |
|---|---|---|
| Ausência de testes automatizados (Vitest) para a TASK-001 | Pendência, não erro | Adicionar antes de considerar a task pronta para merge — critério de aceite não exigiu explicitamente, mas é padrão do projeto |
| `Access-Control-Allow-Origin: "*"` é permissivo para produção | Nota de configuração | Restringir ao domínio real do painel web via variável de ambiente antes de produção; decisão para o Tech Lead, não algo que o Copilot deveria assumir sozinho |
| `authLevel: "anonymous"` no binding do `app.http` | Decisão de design não coberta pelo `plan.md` | Confirmar com o Tech Lead se é intencional para esta fase ou se precisa de autenticação |

---

## Descobertas de ambiente durante a validação

A execução real (não apenas leitura de código) revelou uma cadeia de ajustes de ambiente não descritos no `plan.md` ou no Anexo C, relevantes para o onboarding de outros desenvolvedores do time:

1. **`local.settings.json` e `host.json`** precisaram ser criados manualmente, com `FUNCTIONS_WORKER_RUNTIME: "node"` explícito — sem isso, o Core Tools rejeita a inicialização com "Worker runtime cannot be 'None'".
2. **Azurite** (emulador de Azure Storage) é necessário localmente, mesmo para uma function puramente HTTP — o runtime do Azure Functions faz health check de storage internamente e reporta "unhealthy" sem ele.
3. **Imports ESM exigem extensão `.js` explícita** mesmo em arquivos `.ts`, por conta de `"type": "module"` no `package.json` — o TypeScript não reescreve isso automaticamente na compilação, causando `ERR_MODULE_NOT_FOUND` em runtime.
4. **Divergência entre `outDir` do `tsconfig.json` e o campo `main` do `package.json`**: o `tsc` gerou a estrutura `dist/src/functions/...` (preservando a pasta `src/`), enquanto o `main` esperava `dist/functions/...`. Corrigido ajustando o `main` para `dist/src/functions/**/*.js`. Uma correção mais definitiva seria ajustar o `rootDir` no `tsconfig.json` para eliminar essa duplicação de `src/` dentro de `dist/`, mantendo a convenção de pastas do Anexo C sem esse desvio — não aplicada nesta rodada, registrada como recomendação futura.

Recomenda-se documentar esses quatro pontos no `docs/onboarding.md` do repositório para evitar que cada novo desenvolvedor repita o mesmo processo de diagnóstico.

---

## Síntese

| Item | Status |
|---|---|
| Problema 1 — CORS/OPTIONS bloqueado | Identificado, corrigido, verificado (200 com headers) |
| Problema 1b — CORS ausente em respostas não-OPTIONS | Identificado durante a correção, corrigido, verificado |
| Problema 2 — erro de parsing JSON descartado | Identificado, corrigido, verificado (400 com mensagem específica) |
| Testes automatizados | Pendência sinalizada, não implementada nesta rodada |
| Dependências de ambiente não documentadas | 4 itens registrados para incorporação ao onboarding do projeto |
