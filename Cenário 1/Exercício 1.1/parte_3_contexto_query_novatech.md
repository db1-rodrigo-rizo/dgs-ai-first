# Análise de Orçamento de Contexto por Query — Pipeline RAG NovaTech
**Projeto:** Assistente de IA para Atendimento ao Cliente  
**Modelo LLM:** GPT-4o (janela: 128.000 tokens)  
**Seção:** Parte 3 — Orçamento de Contexto por Query  
**Base:** Estimativas calculadas na Parte 2 (~2,5M tokens indexáveis, ~6.250 chunks de ~400 tokens)

> **Nota de alinhamento com a Parte 2:** A Parte 2 estimou chunks de ~400 tokens como referência de dimensionamento do índice. Esta análise adota **500 tokens por chunk** conforme especificado no escopo — o que representa um tamanho ligeiramente maior por chunk, resultando em ~5.000 chunks no índice (2.500.000 ÷ 500). Os princípios de orçamento de contexto abaixo são válidos para ambos os tamanhos.

---

## 1. Capacidade Teórica por Query

### Decomposição do orçamento de 128.000 tokens

| Componente | Tokens | % da janela |
|---|---:|---:|
| System prompt + instruções | 2.000 | 1,6% |
| Histórico de conversa (estimativa: 3 turnos) | 1.500 | 1,2% |
| Pergunta do usuário (query atual) | 200 | 0,2% |
| Resposta reservada para o modelo (output) | 1.000 | 0,8% |
| **Orçamento disponível para chunks (contexto RAG)** | **123.300** | **96,3%** |

### Capacidade bruta em chunks

```
Orçamento disponível ÷ tokens por chunk
= 123.300 ÷ 500
= 246 chunks (capacidade teórica máxima)
```

| Métrica | Valor |
|---|---:|
| Janela total do GPT-4o | 128.000 tokens |
| Tokens consumidos por infraestrutura de prompt | 4.700 tokens |
| **Orçamento disponível para contexto RAG** | **123.300 tokens** |
| Tamanho do chunk | 500 tokens |
| **Capacidade teórica máxima (chunks por query)** | **~246 chunks** |
| Total de chunks no índice | ~5.000 chunks |
| Proporção do índice que cabe em uma query | **~4,9%** |

O número é tecnicamente impressionante, mas operacionalmente irrelevante: enviar 246 chunks ao GPT-4o não é uma estratégia — é uma transferência de responsabilidade do retriever para o modelo. O modelo não lê 246 chunks com atenção uniforme; ele os lê com atenção degradada, conforme explorado na próxima seção.

---

## 2. Ponto de Equilíbrio Recomendado

### O problema estrutural: atenção não é uniforme

O efeito *lost in the middle*, documentado em pesquisas sobre modelos de linguagem com contexto longo, descreve um comportamento mensurável: o GPT-4o recupera com alta fidelidade informações posicionadas no **início** e no **fim** do contexto, e com fidelidade progressivamente menor as informações posicionadas no **meio**. Em testes com 20+ documentos em contexto, a taxa de utilização correta do conteúdo central cai significativamente — chegando a ser ignorado por completo em contextos muito longos com perguntas diretas.

Para o domínio da NovaTech, isso tem uma consequência concreta: se o chunk que contém o SLA do cliente Silver estiver na posição 8 de 15 chunks enviados, a probabilidade de o modelo utilizá-lo corretamente é menor do que se ele estivesse na posição 1 ou 15.

### Curva de utilidade dos chunks

| Faixa de chunks (top-k) | Qualidade da resposta | Risco de "lost in the middle" | Cobertura do índice |
|---|---|---|---|
| 1–3 chunks | Alta precisão, baixa cobertura | Nenhum | ~0,06% |
| 4–8 chunks | Equilíbrio ótimo para queries simples | Baixo | ~0,1–0,16% |
| **8–12 chunks** | **Equilíbrio ótimo para queries compostas** | **Moderado, gerenciável** | **~0,2%** |
| 13–20 chunks | Cobertura aumenta, mas atenção começa a dispersar | Alto no meio | ~0,3–0,4% |
| 20+ chunks | Rendimento marginal decrescente, risco real de ignorar conteúdo central | Crítico | >0,4% |

### Recomendação para a NovaTech

**Top-k = 8 a 12 chunks como regime padrão**, com as seguintes regras de posicionamento:

1. **Chunk de maior score de relevância → posição 1** (primeiro no contexto)
2. **Segundo chunk mais relevante → última posição** (âncora final)
3. **Chunks de suporte e contexto complementar → posições intermediárias**

Esse ordenamento simula o padrão de atenção do modelo e maximiza a probabilidade de que os dados críticos (valor de SLA, prazo, regra de frete) sejam corretamente utilizados na resposta.

| Parâmetro | Valor recomendado | Justificativa |
|---|---|---|
| Top-k padrão | 8–12 chunks | Cobre queries compostas sem dispersar atenção |
| Top-k para queries simples (1 assunto) | 4–6 chunks | Reduz ruído e custo de inferência |
| Top-k máximo permitido | 15 chunks | Limiar acima do qual o risco supera o benefício |
| Tokens de contexto RAG utilizados (regime padrão) | 4.000–6.000 tokens | 3,2–4,9% da janela — orçamento conservador e eficiente |
| Tokens de contexto RAG utilizados (regime máximo) | 7.500 tokens | 5,9% da janela — ainda seguro |

> A NovaTech utiliza **apenas 3–6% da janela disponível do GPT-4o** no regime recomendado. A janela larga do modelo (128K) não é uma razão para enviar mais contexto — é uma margem de segurança para histórico de conversa longo e respostas detalhadas.

---

## 3. Queries Multi-Chunk: o Caso da Carga Perigosa

### A query de referência

> *"Qual é o SLA para uma entrega de carga perigosa na região norte para um cliente Silver?"*

Essa query é representativa do tipo mais desafiador no domínio logístico: ela combina **quatro dimensões de filtragem simultâneas** que provavelmente estão em documentos completamente diferentes.

### Decomposição das dimensões de recuperação

| Dimensão | Fonte provável | Tipo de chunk esperado |
|---|---|---|
| SLA por tipo de cliente (Silver) | PDF de política comercial ou Wiki Confluence | Tabela de níveis de serviço por tier |
| Regras para carga perigosa (IMDG/ANTT) | PDF de norma de segurança de carga | Texto normativo com restrições e procedimentos |
| Prazos por região (Norte) | Planilha de frete convertida em regras (Parte 1, estratégia A) | Chunk de regra com faixa geográfica |
| Interseção: carga perigosa + região norte | Possivelmente inexistente como chunk único | Requer inferência cruzada pelo modelo |

### O problema: o chunk que responde à pergunta pode não existir

A documentação da NovaTech foi criada por três áreas diferentes (Operações, Compliance, Comercial) sem processo unificado. É altamente provável que **não exista um documento que combine explicitamente** as quatro dimensões da query. O pipeline RAG terá que:

1. Recuperar o SLA geral de clientes Silver (chunk A)
2. Recuperar as restrições operacionais de carga perigosa (chunk B)
3. Recuperar o prazo base para a região Norte (chunk C)
4. Deixar para o GPT-4o a tarefa de inferir se há interseção ou conflito entre A, B e C

### Diagrama de fluxo de retrieval multi-chunk

```
Query: "SLA | carga perigosa | região norte | cliente Silver"
          │
          ▼
   [Query Expansion / Decomposição]
   ┌──────────────────────────────────────┐
   │ Sub-query 1: "SLA cliente Silver"    │
   │ Sub-query 2: "carga perigosa normas" │
   │ Sub-query 3: "prazo região norte"    │
   └──────────────────────────────────────┘
          │
          ▼
   [Retrieval paralelo com top-k=4 por sub-query]
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │ 4 chunks│  │ 4 chunks│  │ 4 chunks│
   │ (SLA)   │  │ (perig.)│  │ (norte) │
   └─────────┘  └─────────┘  └─────────┘
          │
          ▼
   [Re-ranking + deduplicação → top 10 chunks únicos]
          │
          ▼
   [Montagem do contexto com posicionamento estratégico]
   Posição 1:  chunk SLA Silver (maior relevância)
   Posição 10: chunk prazo Norte (segunda maior relevância)
   Posições 2–9: chunks de suporte (normas ANTT, restrições operacionais)
          │
          ▼
   [GPT-4o sintetiza resposta com citação de fonte por dimensão]
```

### Estratégia recomendada: Query Decomposition + Retrieval Paralelo

Em vez de enviar a query completa ao retriever e esperar que a busca por similaridade semântica encontre chunks que cubram todas as quatro dimensões simultaneamente — o que raramente acontece — o pipeline deve decompor a query em sub-queries especializadas antes do retrieval.

| Etapa | Mecanismo | Ferramenta no stack Azure |
|---|---|---|
| Decomposição da query | LLM identifica dimensões distintas e gera sub-queries | GPT-4o com prompt de decomposição |
| Retrieval paralelo | Top-k=4 por sub-query, executados em paralelo | Azure AI Search (múltiplas chamadas async) |
| Re-ranking | Modelo de re-ranking pontua chunks pelo contexto completo da query original | Azure AI Search Semantic Ranker |
| Deduplicação | Chunks duplicados entre sub-queries são removidos | Lógica de aplicação (hash de chunk_id) |
| Posicionamento | Chunks ordenados por relevância com posicionamento estratégico (início/fim) | Lógica de montagem do prompt |
| Síntese | GPT-4o recebe chunks posicionados + instrução para citar fonte por dimensão | Prompt engineering no system prompt |

### Risco residual: contradição entre chunks

Se o chunk A (SLA Silver) define prazo de 5 dias úteis e o chunk B (normas de carga perigosa) define que cargas IMDG classe 3 têm prazo mínimo de 8 dias — e não existe um documento que reconcilie essa contradição — o GPT-4o pode:

- Apresentar os dois valores sem resolver a contradição *(comportamento correto, mas frustrante para o atendente)*
- Escolher um dos valores sem transparência *(comportamento perigoso)*
- Sinalizar que a resposta requer validação humana *(comportamento ideal, que deve ser instruído explicitamente no system prompt)*

**Recomendação:** o system prompt deve instruir explicitamente o modelo a identificar e reportar contradições entre fontes, incluindo os títulos dos documentos em conflito. Isso transforma um risco de resposta errada em uma oportunidade de identificar gaps de governança documental — problema que a NovaTech já tem hoje e que o assistente pode ajudar a mapear sistematicamente.

---

## Resumo Executivo da Análise de Contexto

| Parâmetro | Valor |
|---|---:|
| Capacidade teórica máxima (chunks/query) | ~246 chunks |
| Regime recomendado (top-k padrão) | 8–12 chunks |
| Tokens de contexto RAG por query (regime padrão) | 4.000–6.000 tokens |
| % da janela do GPT-4o utilizada (regime padrão) | ~3–5% |
| Top-k para queries multi-dimensionais | até 15 chunks (via decomposição + re-ranking) |
| Chunks totais no índice | ~5.000 chunks |
| % do índice coberta por query | ~0,2% |