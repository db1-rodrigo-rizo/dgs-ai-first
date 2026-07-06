# Mapeamento de Criação e Consumo por Skill

> Para cada skill da árvore: nome, descrição/frase-ativação, quem cria (papel), quem consome (papel + agente), e frequência de uso estimada.

---

## Nível Foundation

### `typescript-conventions`
- **Descrição (frase-ativação):** "sempre que um agente for gerar ou editar um arquivo `.ts`/`.tsx` no repositório."
- **Cobre:** strict mode, convenção de nomes, organização de imports, uso de tipos vs. `any`, exports nomeados vs. default.
- **Quem cria:** Tech Lead.
- **Quem consome:** Todos os devs, via Copilot e Claude, em toda geração de código TypeScript.
- **Frequência de uso:** Muito alta — praticamente toda tarefa de código passa por aqui.

### `error-handling`
- **Descrição (frase-ativação):** "sempre que um agente for gerar código que possa falhar (chamadas externas, parsing, validação) ou lançar/capturar exceções."
- **Cobre:** custom errors, quando logar vs. propagar, padrão de retry, como não silenciar exceções.
- **Quem cria:** Tech Lead.
- **Quem consome:** Devs, via Copilot e Claude, especialmente em `src/services/` e `src/functions/`.
- **Frequência de uso:** Alta — toda integração com Azure OpenAI/AI Search passa por tratamento de erro.

### `project-structure`
- **Descrição (frase-ativação):** "sempre que um agente precisar decidir em qual pasta criar um novo arquivo, ou como nomear um módulo novo."
- **Cobre:** onde vive cada tipo de artefato (`src/functions/`, `src/services/`, `src/pipeline/`, etc.), convenção de nomes de arquivo, o que vai em `shared/`.
- **Quem cria:** Tech Lead.
- **Quem consome:** Todos os papéis que geram artefatos no repositório — Devs via Copilot e Claude; Product Specialist via Claude, ao criar specs; QA via Claude, ao criar fixtures em `tests/fixtures/`.
- **Frequência de uso:** Alta — é a primeira coisa consultada antes de criar qualquer arquivo novo.

### `logging-standards`
- **Descrição (frase-ativação):** "sempre que um agente for adicionar logging/observabilidade a uma função ou serviço."
- **Cobre:** uso de pino (nunca `console.log`), níveis de log (info/warn/error), o que não deve ser logado (PII, conteúdo de perguntas — referência ao `questionLength` em vez do texto completo, formato de campos estruturados.
- **Quem cria:** Tech Lead.
- **Quem consome:** Devs, via Copilot e Claude.
- **Frequência de uso:** Alta — presente em praticamente todo handler e serviço.

### `env-config`
- **Descrição (frase-ativação):** "sempre que um agente precisar ler configuração de ambiente, segredos, ou strings de conexão."
- **Cobre:** uso de `local.settings.json` vs. variáveis de ambiente reais, o que nunca deve ser hardcoded, convenção de nomes de variável (ex: `AZURE_OPENAI_ENDPOINT`).
- **Quem cria:** Tech Lead.
- **Quem consome:** Devs, via Copilot e Claude, especialmente ao integrar com Azure OpenAI/AI Search.
- **Frequência de uso:** Média — usada sempre que uma nova integração externa é adicionada, não em toda task.

---

## Nível Domain

### `azure-functions-endpoint`
- **Descrição (frase-ativação):** "sempre que um agente for criar ou modificar um Azure Function HTTP trigger."
- **Cobre:** estrutura handler + validator, tratamento de CORS em todas as respostas (não só preflight), status codes por tipo de erro.
- **Quem cria:** Tech Lead (com input do Dev que implementou o primeiro endpoint real).
- **Quem consome:** Devs, via Copilot, a cada novo endpoint (query, feedback, health).
- **Frequência de uso:** Alta — pelo menos 3 endpoints previstos na arquitetura (query, feedback, health).

### `testing-patterns`
- **Descrição (frase-ativação):** "sempre que um agente for gerar um teste unitário ou de integração."
- **Cobre:** Vitest, estrutura arrange/act/assert, mocking com msw, uso de fixtures (`tests/fixtures/`).
- **Quem cria:** QA.
- **Quem consome:** Devs, via Copilot; QA, via Claude, para revisão.
- **Frequência de uso:** Alta — todo endpoint/serviço precisa de teste correspondente.

### `react-components`
- **Descrição (frase-ativação):** "sempre que um agente for criar um componente React para o painel web."
- **Cobre:** estrutura de pastas em `src/web/src/components/`, convenção de props, estilo (se usa Tailwind, styled-components, etc. — decisão do Tech Lead).
- **Quem cria:** Tech Lead ou Dev sênior com experiência frontend.
- **Quem consome:** Devs, via Copilot, ao construir o painel web (cards de resposta, formulário de feedback).
- **Frequência de uso:** Média — painel web é um dos 4 componentes da arquitetura, mas menos frequente que o backend.

### `technical-documentation`
- **Descrição (frase-ativação):** "sempre que um agente for gerar um ADR ou README de módulo."
- **Cobre:** template de ADR (Contexto, Decisão, Consequências, Alternativas — já definido no Anexo C), estrutura mínima de um README de módulo.
- **Quem cria:** Dev sênior ou Tech Lead.
- **Quem consome:** Devs, via Claude ou Copilot, ao documentar decisões durante implementação; Tech Lead, via Claude, ao revisar.
- **Frequência de uso:** Média-baixa — um ADR por decisão arquitetural relevante, não por task.

### `spec-sdd-template`
- **Descrição (frase-ativação):** "sempre que um agente for gerar ou revisar um requirements.md, plan.md ou tasks.md."
- **Cobre:** estrutura SDD (outcomes, scope boundaries, constraints, verification criteria para requirements; approach, technical decisions, dependencies para plan; ID/critérios de aceite/dependências/estimativa para tasks).
- **Quem cria:** Product Specialist (dono do processo SDD), validado pelo Tech Lead.
- **Quem consome:** Product Specialist, via Claude, para requirements; Tech Lead, via Claude, para plan; Dev, via Claude, para tasks.
- **Frequência de uso:** Alta — um ciclo completo por módulo (5 módulos previstos), recorrente a cada nova feature.

---

## Nível Artifact

### `create-rag-endpoint`
- **Descrição (frase-ativação):** "crie um endpoint RAG completo (recebe pergunta, busca chunks, monta prompt, chama LLM, retorna resposta com fonte)."
- **Cobre:** receita passo a passo combinando `azure-functions-endpoint` + integração com Azure AI Search/OpenAI + tratamento de context budget (ADR-0002) + metadado de vigência (ADR-0003).
- **Quem cria:** Dev sênior (após implementar o primeiro endpoint RAG real, extraindo o padrão).
- **Quem consome:** Devs, via Copilot, a cada novo endpoint com padrão RAG.
- **Frequência de uso:** Média — o query endpoint é o caso principal nesta fase; outros podem surgir.

### `create-integration-test`
- **Descrição (frase-ativação):** "crie um teste de integração para um endpoint Azure Function."
- **Cobre:** receita concreta com placeholders, exemplos DO/DON'T (teste bem escrito vs. teste como `expect(result).toBeDefined()`), depende de `testing-patterns` (Domain).
- **Quem cria:** QA.
- **Quem consome:** Devs, via Copilot, a cada novo endpoint implementado.
- **Frequência de uso:** Alta — acompanha 1:1 a criação de endpoints.

### `create-react-card`
- **Descrição (frase-ativação):** "crie um card de resposta ou formulário de feedback para o painel web."
- **Cobre:** receita concreta para os dois componentes citados no enunciado (card de resposta, formulário de feedback), depende de `react-components` (Domain).
- **Quem cria:** Dev com experiência frontend.
- **Quem consome:** Devs, via Copilot, ao construir telas do painel web.
- **Frequência de uso:** Baixa-média — poucos componentes previstos nesta fase (cards de resposta, formulário de feedback).

### `create-adr`
- **Descrição (frase-ativação):** "documente uma decisão arquitetural como ADR."
- **Cobre:** receita de preenchimento do template `docs/adr/template.md`, com exemplo de ADR real preenchido (ex: um ADR fictício sobre a escolha de CORS `withCors()`).
- **Quem cria:** Dev sênior ou Tech Lead.
- **Quem consome:** Devs e Tech Lead, via Claude (geração de texto estruturado, sem necessidade de execução de código).
- **Frequência de uso:** Baixa — um ADR por decisão relevante, não por task.

### `create-product-spec`
- **Descrição (frase-ativação):** "escreva um requirements.md seguindo o formato SDD para um novo módulo."
- **Cobre:** receita de preenchimento do `spec-sdd-template` (Domain) com exemplo real (o `requirements.md` do query endpoint).
- **Quem cria:** Product Specialist.
- **Quem consome:** Product Specialist, via Claude (principal); Tech Lead, via Claude, ao gerar o `plan.md` a partir dela.
- **Frequência de uso:** Média — uma por módulo.

---

## Tabela-resumo

| Skill | Nível | Criado por | Consumido por (papel) | Agente(s) usado(s) |
|---|---|---|---|---|
| typescript-conventions | Foundation | Tech Lead | Todos os devs | Copilot, Claude |
| error-handling | Foundation | Tech Lead | Devs | Copilot, Claude |
| project-structure | Foundation | Tech Lead | Devs, Product Specialist, QA | Copilot, Claude |
| logging-standards | Foundation | Tech Lead | Devs | Copilot, Claude |
| env-config | Foundation | Tech Lead | Devs | Copilot, Claude |
| azure-functions-endpoint | Domain | Tech Lead + Dev sênior | Devs | Copilot |
| testing-patterns | Domain | QA | Devs, QA | Copilot, Claude |
| react-components | Domain | Tech Lead / Dev sênior | Devs | Copilot |
| technical-documentation | Domain | Dev sênior / Tech Lead | Devs, Tech Lead | Claude |
| spec-sdd-template | Domain | Product Specialist | Product Specialist, Tech Lead, Dev | Claude |
| create-rag-endpoint | Artifact | Dev sênior | Devs | Copilot |
| create-integration-test | Artifact | QA | Devs | Copilot |
| create-react-card | Artifact | Dev (frontend) | Devs | Copilot |
| create-adr | Artifact | Dev sênior / Tech Lead | Devs, Tech Lead | Claude |
| create-product-spec | Artifact | Product Specialist | Product Specialist, Tech Lead | Claude |
