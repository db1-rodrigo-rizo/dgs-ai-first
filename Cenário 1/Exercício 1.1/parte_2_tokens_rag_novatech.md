# Estimativa de Tamanho da Base em Tokens — Pipeline RAG NovaTech
**Projeto:** Assistente de IA para Atendimento ao Cliente  
**Seção:** Parte 2 — Estimativa de Base em Tokens  
**Modelo LLM:** GPT-4o  
**Regra de conversão adotada:** 1 token ≈ 0,75 palavras → 1 palavra ≈ 1,333 tokens

---

## 1. Critérios de Estimativa de Palavras por Fonte

### PDFs — Justificativa da média adotada (250 palavras/página)

Documentação corporativa de logística é caracteristicamente densa em tabelas, listas numeradas e campos rotulados — estruturas que ocupam espaço visual mas geram menos palavras do que prosa corrida. Uma página A4 de texto puro chegaria a 400–500 palavras; uma página de relatório executivo com gráficos fica em torno de 200. Para a NovaTech, o mix inclui manuais de procedimento operacional (mais densos em texto), tabelas de frete (muito densas em números, esparsas em palavras) e normas de segurança (texto corrido com listas). **Adota-se 250 palavras/página como média conservadora**, compatível com documentação técnica e operacional do setor logístico com presença relevante de elementos não textuais.

### Planilhas XLSX — Justificativa da média adotada (800 palavras/planilha)

Planilhas de referência logística não são documentos de texto — são matrizes de valores. Uma planilha com 20 linhas × 15 colunas de dados numéricos mais cabeçalhos tem aproximadamente 300 células preenchidas; estimando em média 3 "palavras" por célula (cabeçalhos verbosos + valores + unidades), chegamos a ~900 palavras por aba. Considerando que parte das planilhas tem múltiplas abas mas muitas células são numéricas puros (peso, valor, prazo) que contribuem pouco para a semântica textual, **adota-se 800 palavras/planilha** como estimativa que reflete o conteúdo semanticamente útil para indexação RAG — excluindo valores numéricos isolados sem contexto, que serão melhor representados nas regras geradas conforme estratégia A da Parte 1.

---

## 2. Cálculo por Fonte

### Fonte 1 — PDFs (SharePoint)

| Parâmetro | Valor |
|---|---|
| Número de documentos | 800 |
| Média de páginas por documento | 10 |
| Total de páginas | 8.000 |
| Palavras por página (estimativa) | 250 |
| **Total de palavras** | **2.000.000** |
| Fator de conversão (palavras → tokens) | ÷ 0,75 |
| **Total de tokens (bruto)** | **~2.667.000** |

### Fonte 2 — Wiki Confluence

| Parâmetro | Valor |
|---|---|
| Número de páginas | 400 |
| Palavras por página (fornecido) | 1.500 |
| **Total de palavras** | **600.000** |
| Fator de conversão (palavras → tokens) | ÷ 0,75 |
| **Total de tokens (bruto)** | **~800.000** |

### Fonte 3 — Planilhas XLSX

| Parâmetro | Valor |
|---|---|
| Número de planilhas | 50 |
| Palavras por planilha (estimativa) | 800 |
| **Total de palavras** | **40.000** |
| Fator de conversão (palavras → tokens) | ÷ 0,75 |
| **Total de tokens (bruto)** | **~53.000** |

---

## 3. Consolidado Bruto

| Fonte | Total de Palavras | Total de Tokens (bruto) | % do total |
|---|---:|---:|---:|
| PDFs — SharePoint | 2.000.000 | ~2.667.000 | 76,9% |
| Wiki — Confluence | 600.000 | ~800.000 | 23,1% |
| Planilhas XLSX | 40.000 | ~53.000 | 1,5% |
| **Subtotal** | **2.640.000** | **~3.520.000** | **100%** |

> **Nota:** As planilhas representam menos de 2% do volume em tokens — confirmando que o risco que elas representam (identificado na Parte 1) é de qualidade, não de escala.

---

## 4. Fator de Correção para Conteúdo Não Textual

### Definição do fator: **0,70** (desconto de 30% sobre o total bruto)

O fator de correção responde à seguinte pergunta: *de todo o conteúdo identificado nas fontes, qual fração é efetivamente texto indexável pelo pipeline RAG?*

A justificativa é composta por três componentes:

| Componente | Fonte afetada | Desconto estimado | Racional |
|---|---|---|---|
| Imagens, fluxogramas e diagramas embutidos | PDFs | ~15% das páginas são predominantemente visuais | Manuais de procedimento logístico com frequência apresentam fluxogramas de processo e fotos de identificação de carga; essas páginas geram pouco ou nenhum texto útil via extração padrão |
| Tabelas densas em números (células sem contexto semântico) | PDFs + XLSX | ~10% do conteúdo extraído | Linhas de tabela com apenas valores numéricos (ex: `"SP → RJ | 100 | 150 | 2 | 3 | 1.2%"`) sem reconstituição de cabeçalho não contribuem para retrieval semântico e inflariam o índice com ruído |
| Macros não resolvidas e artefatos de exportação | Confluence | ~5% do conteúdo exportado | Tags de macro não renderizadas (`{include}`, `{excerpt}`), metadados XML de formatação e âncoras internas que sobrevivem à exportação como texto literal |

**Fator combinado adotado: 0,70** — conservador o suficiente para não subestimar o volume real, sem ser pessimista a ponto de ignorar que a maior parte da documentação da NovaTech é texto corrido em manuais e políticas.

> Para projetos com alta proporção de documentos escaneados de baixa qualidade ou planilhas majoritariamente numéricas, o fator poderia cair para 0,60. Para bases predominantemente textuais e bem estruturadas, 0,80 seria adequado. O valor 0,70 reflete o perfil misto da NovaTech.

---

## 5. Total Ajustado

| | Tokens |
|---|---:|
| Total bruto (antes da correção) | ~3.520.000 |
| Fator de correção | × 0,70 |
| **Total ajustado (tokens indexáveis)** | **~2.464.000** |

Arredondando para comunicação com stakeholders: **~2,5 milhões de tokens** de conteúdo efetivamente indexável.

---

## 6. Implicações para o Dimensionamento do Pipeline

| Aspecto | Referência |
|---|---|
| Tamanho típico de chunk (com overlap) | ~400 tokens |
| Número estimado de chunks no índice | ~2.500.000 ÷ 400 = **~6.250 chunks** |
| Janela de contexto do GPT-4o | 128.000 tokens |
| Chunks que cabem em uma única chamada (teórico) | ~320 chunks |
| Chunks típicos por chamada RAG (prática recomendada) | 5–15 chunks (top-k retrieval) |

O volume total de ~6.250 chunks é **gerenciável por qualquer solução de vector store enterprise** (Azure AI Search, Pinecone, Weaviate) sem necessidade de sharding ou arquitetura distribuída. Isso é uma vantagem significativa: o projeto pode usar Azure AI Search na camada Basic ou Standard S1 sem pressão de escala, reservando o orçamento para a qualidade do pipeline de ingestão — que, conforme identificado na Parte 1, é onde os riscos reais estão.