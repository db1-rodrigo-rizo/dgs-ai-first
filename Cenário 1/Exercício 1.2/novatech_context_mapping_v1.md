# Mapeamento de Contexto — NovaTech Assistant v1

**Projeto:** NovaTech Logística — Assistente de Consulta Documental  
**Versão do System Prompt:** v1  
**Data:** 2026-06-05  

---

## Definições

| Tipo | Descrição |
|------|-----------|
| **Estático** | Partes enviadas em toda query, independente da pergunta ou do cliente. Fixas, controladas na configuração do sistema. |
| **Dinâmico** | Partes que mudam a cada query — dependem da pergunta do atendente, dos chunks recuperados pelo pipeline RAG, do perfil do cliente ou do histórico da conversa. |

> **Regra de estimativa:** 1 token = 1 palavra.

---

## Tabela de Mapeamento

| Parte do contexto | Estático / Dinâmico | Tamanho estimado (tokens) | Observação |
|---|---|---|---|
| **Identidade e propósito** | Estático | ~114 | Nunca muda. Define o escopo e a persona do assistente para toda a vida útil da v1. |
| **Regras e guardrails (R1–R5)** | Estático | ~234 | Comportamento fixo de compliance. Só muda se houver nova versão do prompt. |
| **Estrutura esperada de resposta** | Estático | ~162 | Template de output fixo. O modelo renderiza o formato; o conteúdo varia a cada query. |
| **Regras de uso dos chunks** (priorização, citação, confiança) | Estático | ~202 | Instruções sobre como processar os chunks. Fixas — os chunks em si é que são dinâmicos. |
| **Schema de injeção de chunk** (template de formato) | Estático | ~23 | Declara o formato esperado do payload RAG: `[CHUNK n] · Fonte · Conteúdo`. Apenas o wrapper estrutural, não o conteúdo. |
| **Ordem de prioridade e resolução de conflitos** | Estático | ~228 | Regra determinística em 3 critérios. Fixo até revisão editorial da política de fontes. |
| **Chunks RAG injetados** | Dinâmico | ~4.000 (8 × 500) | Principal variável do contexto. Depende inteiramente da semântica da pergunta e do índice vetorial. Pode variar de 0 (nenhum chunk recuperado) a >6.000 se chunks forem maiores. |
| **Pergunta do atendente** (user message) | Dinâmico | ~15–30 | Pequeno em tokens, mas determina 100% do que o RAG vai recuperar. É o gatilho de toda a cadeia. |
| **Histórico de conversa** (turns anteriores) | Dinâmico | 0–300+ | Ausente na v1 (single-turn implícito). Se multi-turn for habilitado, cresce linearmente com o número de turnos. Risco de context overflow em sessões longas. |
| **Perfil do atendente / contexto do cliente** | Não presente (v1) | — | Extensão prevista: injetar segmento do cliente (premium, padrão) para ativar regras de SLA específicas. Quando implementado, será dinâmico: ~50–100 tokens. |

---

## Totais e Intervalos

### Tokens estáticos (system prompt fixo)

| Seção | Tokens |
|-------|--------|
| Identidade e propósito | ~114 |
| Regras e guardrails (R1–R5) | ~234 |
| Estrutura esperada de resposta | ~162 |
| Regras de uso dos chunks | ~202 |
| Schema de injeção de chunk | ~23 |
| Ordem de prioridade e conflitos | ~228 |
| **Total estático** | **~963** |

### Estimativa do contexto total por query

| Cenário | Composição | Total estimado |
|---------|------------|----------------|
| Mínimo (sem histórico) | 963 estático + 4.000 chunks + 20 query | **~4.983 tokens** |
| Típico (com 2 turnos de histórico) | 963 + 4.000 + 20 + 300 histórico | **~5.283 tokens** |
| Degradado (chunks maiores, histórico longo) | 963 + 6.000 + 30 + 600 | **~7.593 tokens** |

### Distribuição percentual — query típica

```
System prompt estático  ████░░░░░░░░░░░░░░░░  19%  (~963 tokens)
Chunks RAG              ████████████████░░░░  80%  (~4.000 tokens)
Query do atendente      ░░░░░░░░░░░░░░░░░░░░   1%  (~20 tokens)
```

---

## Observações Operacionais

### 1. O custo é dominado pelos chunks, não pelo system prompt

80% do contexto consumido em cada query vem dos chunks RAG. Isso tem duas implicações diretas:

- O custo por token é determinado principalmente pelo volume de chunks. Otimizar o tamanho médio do chunk (ex: reduzir de 500 para 350 tokens) tem impacto financeiro maior do que comprimir o system prompt.
- Se o modelo apresentar comportamento inesperado, o problema estará provavelmente na qualidade do chunk recuperado — não nas regras do prompt.

### 2. O schema de injeção de chunk é um ponto de acoplamento crítico

A seção de 23 tokens que declara o formato `[CHUNK n] · Fonte · Conteúdo` precisa bater exatamente com o que o pipeline RAG injeta. Se o pipeline mudar o schema (ex: adicionar campos `score` ou `data_revisao` no cabeçalho do chunk), o system prompt precisa ser atualizado na mesma release. Tratar como contrato de interface entre equipes de prompt e pipeline.

### 3. Histórico de conversa: risco de overflow em v2

A v1 é implicitamente single-turn, o que é seguro. Se multi-turn for habilitado futuramente, o contexto cresce a cada turno e pode atingir o limite do modelo em sessões longas sem aviso. Recomendação: definir explicitamente a janela máxima de histórico (ex: últimos 3 turnos) antes de implementar.

### 4. Slot reservado para perfil do cliente

A linha "Não presente (v1)" na tabela está deliberadamente documentada para sinalizar o ponto de extensão. Quando o time de produto decidir segmentar respostas por tipo de cliente (ex: SLA diferente para clientes premium), a injeção acontece aqui como contexto dinâmico adicional, sem necessidade de reescrever as demais seções do prompt.

---

## Referências

- [System Prompt v1 — NovaTech Assistant](./System_Prompt_v1.md)
