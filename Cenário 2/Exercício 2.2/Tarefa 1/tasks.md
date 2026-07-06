# Tasks — Query Endpoint

> Gerado a partir de `specs/query-endpoint/plan.md`. Cada task é atômica: implementável e testável de forma independente, respeitando as dependências declaradas.

---

## TASK-001 — Setup do endpoint HTTP e validação de input

**Descrição:** Criar o Azure Function HTTP trigger `POST /api/query` com validação de input via Zod. Não inclui lógica de busca ou geração — apenas recepção, validação e retorno de erro estruturado para input inválido.

**Critérios de aceite:**
- Endpoint responde a `POST /api/query` e rejeita outros métodos com `405`.
- Schema Zod valida que o body contém `question: string` (não vazio, máx. 2000 caracteres).
- Input inválido retorna `400` com corpo JSON `{ error: string, details: [...] }`.
- Input válido retorna `200` com payload placeholder (ex: `{ received: true }`) — a lógica real vem nas tasks seguintes.
- Log estruturado (pino) registra toda requisição recebida, com nível `info` para válidas e `warn` para inválidas.

**Dependências:** nenhuma (task inicial).

**Estimativa:** P

---

## TASK-002 — Geração de embedding da pergunta via Azure OpenAI

**Descrição:** Implementar o serviço que recebe a pergunta validada (de TASK-001) e gera o embedding correspondente via Azure OpenAI, isolado como módulo em `src/services/`.

**Critérios de aceite:**
- Função `generateEmbedding(question: string): Promise<number[]>` implementada em `src/services/completion.ts` (ou arquivo dedicado, conforme convenção do Anexo C).
- Retry com exponential backoff (mínimo 3 tentativas) em caso de erro 429/5xx do Azure OpenAI.
- Erro após esgotar tentativas propaga uma exception customizada (`EmbeddingGenerationError`), não um erro genérico.
- Teste unitário cobre: sucesso, falha após retries esgotados, e formato do vetor retornado.

**Dependências:** TASK-001 (precisa da pergunta já validada).

**Estimativa:** M

---

## TASK-003 — Busca dos top-5 chunks no Azure AI Search

**Descrição:** Implementar o serviço de busca semântica que recebe o embedding (de TASK-002) e retorna os 5 chunks mais relevantes do índice.

**Critérios de aceite:**
- Função `searchChunks(embedding: number[], topK: number = 5): Promise<Chunk[]>` implementada em `src/services/search.ts`.
- Cada `Chunk` retornado contém, no mínimo: `content`, `source_document`, `section`, `vigencia` (metadado de versão, conforme ADR-0003).
- Retry com exponential backoff para falhas transitórias do Azure AI Search.
- Se a busca retornar 0 resultados, a função retorna array vazio (não lança exceção) — o tratamento de "sem resposta" é responsabilidade da task de geração de resposta (TASK-005).
- Teste unitário com mock do Azure AI Search cobre: retorno normal, retorno vazio, e falha após retries.

**Dependências:** TASK-002 (precisa do embedding gerado).

**Estimativa:** M

---

## TASK-004 — Montagem do prompt respeitando o context budget

**Descrição:** Implementar a função de montagem do prompt final, combinando system prompt + chunks recuperados + pergunta, respeitando o orçamento de tokens definido na ADR-0002 (~4K system + ~8K chunks).

**Critérios de aceite:**
- Função `buildPrompt(chunks: Chunk[], question: string, history?: Message[]): Prompt` implementada em `src/services/prompt-builder.ts`.
- System prompt é carregado de `/prompts/system-prompt.md` (não hardcoded no código).
- Se o total de tokens dos chunks exceder ~8K, a função trunca pelos chunks de menor relevância primeiro (mantendo os mais relevantes), e registra um log `warn` informando quantos chunks foram descartados.
- Quando dois chunks recuperados referenciam o mesmo documento em versões diferentes (metadado de vigência divergente), o prompt inclui instrução explícita ao modelo para priorizar a versão vigente e mencionar a existência da anterior (conforme ADR-0003).
- Teste unitário cobre: chunks dentro do budget, chunks excedendo o budget (trunca corretamente), e caso de documentos contraditórios.

**Dependências:** TASK-003 (precisa dos chunks recuperados).

**Estimativa:** M

---

## TASK-005 — Chamada ao GPT-4o e construção da resposta final

**Descrição:** Implementar a chamada ao Azure OpenAI (GPT-4o) com o prompt montado (TASK-004), e estruturar a resposta HTTP final incluindo o campo `source_document`.

**Critérios de aceite:**
- Função `generateAnswer(prompt: Prompt): Promise<AnswerResponse>` implementada em `src/services/completion.ts`.
- `AnswerResponse` inclui obrigatoriamente: `answer: string`, `source_document: string[]` (um ou mais documentos citados), `confidence: "high" | "low"`.
- Quando nenhum chunk relevante foi encontrado (array vazio vindo de TASK-003), a resposta retorna mensagem padrão de "não encontrado" (`confidence: "low"`, `source_document: []`), sem chamar o GPT-4o desnecessariamente.
- Retry com exponential backoff para falhas transitórias do Azure OpenAI.
- Endpoint (TASK-001) integrado a esta função retorna `200` com o `AnswerResponse` completo.
- Teste de integração cobre: resposta com fonte, resposta de baixa confiança, e resposta "não encontrado".

**Dependências:** TASK-004 (precisa do prompt montado); TASK-001 (integração final ao endpoint).

**Estimativa:** G

---

## Resumo de dependências

```
TASK-001 (setup + validação)
   └── TASK-002 (embedding)
         └── TASK-003 (busca chunks)
               └── TASK-004 (monta prompt)
                     └── TASK-005 (chamada GPT-4o + resposta final) ── integra de volta em TASK-001
```

## Notas

- A ordem reflete o pipeline sequencial descrito no `plan.md`, mas cada task é isolável: TASK-002 e TASK-003 podem ser testadas com mocks sem que as demais estejam prontas.
- Dependências externas ao escopo deste `tasks.md` (não geram task própria, mas bloqueiam execução em ambiente real): índice do Azure AI Search populado (pipeline de ingestão) e `/prompts/system-prompt.md` finalizado — ambas already listadas em `plan.md` como *Dependencies*.
- TASK-001 é a primeira task a ser implementada (Exercício 2.2, item 2).
