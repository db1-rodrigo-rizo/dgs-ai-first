# Análise Técnica de Viabilidade — Pipeline RAG NovaTech

**Projeto:** Assistente de IA para Atendimento ao Cliente  
**Modelo LLM de referência:** GPT-4o  
**Destinatário:** Tech Lead do Projeto  
**Revisão:** Consolidação das Partes 1–4 da análise técnica  

---

## 1. Introdução e Contexto do Projeto

A NovaTech é uma empresa de logística com 1.200 funcionários cuja operação depende de um corpus documental extenso e heterogêneo. A equipe de atendimento ao cliente (45 pessoas) processa em média 320 chamados por dia, dos quais aproximadamente 60% exigem consulta à documentação interna. O tempo médio atual de busca é de 12 minutos por chamado; a meta estabelecida pela diretoria é reduzir esse indicador para menos de 2 minutos — uma redução de 83%.

O problema não é apenas de acesso: a documentação está distribuída em três fontes com formatos, ciclos de atualização e responsáveis distintos, sem processo unificado de revisão. Há casos documentados de contradições entre versões, que hoje são resolvidos informalmente ("perguntando para quem sabe"). Esse padrão de resolução não escala, não é auditável e é exatamente o que o assistente de IA deve substituir — com a ressalva de que o assistente só poderá ser mais confiável do que o processo atual se o pipeline de ingestão for construído com rigor técnico suficiente para não introduzir novos erros.

### 1.1 Fontes de Dados

| Fonte | Volume | Formatos | Ciclo de atualização | Responsável |
|---|---|---|---|---|
| SharePoint corporativo | ~800 documentos | PDF, Word (.docx) | Mensal | Operações, Compliance, Comercial |
| Wiki Confluence | ~400 páginas | HTML/XML (macros customizadas) | Mensal | Operações, Compliance, Comercial |
| Pasta compartilhada na rede | ~50 planilhas (estimado) | XLSX | Mensal | Operações, Comercial |

### 1.2 Restrições e Premissas do Projeto

- A NovaTech possui licenças Microsoft 365 E3 e pode provisionar Azure AI Services — o stack técnico será construído sobre esse ecossistema.
- O prazo total disponível é de 3 meses, cobrindo discovery, desenvolvimento e go-live.
- A integração final deve ocorrer no ambiente Microsoft (Microsoft Teams + SharePoint).
- O modelo LLM de referência para esta análise é o GPT-4o (janela de contexto de 128.000 tokens).

### 1.3 Escopo desta Análise

Este documento consolida a análise técnica de viabilidade do pipeline RAG em quatro dimensões: caracterização das fontes de dados e seus desafios de ingestão; estimativa do volume total indexável em tokens; orçamento de contexto por query e estratégia de retrieval; e estratégia de chunking por tipo de fonte. A seção 6 sintetiza os riscos técnicos críticos que condicionam o sucesso do projeto.

---

## 2. Análise por Tipo de Fonte

Esta seção descreve, para cada tipo de fonte, o desafio técnico específico para o pipeline RAG, o impacto esperado na qualidade das respostas caso o problema não seja tratado, e a estratégia de tratamento recomendada. As estratégias aqui descritas são insumo direto para a definição de chunking na seção 5.

### 2.1 PDFs com Tabelas Complexas (SharePoint)

**Desafio:** Tabelas de frete com 15 ou mais colunas (origem, destino, tipo de carga, faixas de peso, prazos em dias úteis e corridos, modal, taxa de redespacho, coeficientes de ajuste) perdem sua estrutura relacional quando convertidas para texto plano por extratores PDF convencionais. O significado de uma célula é definido pelo cruzamento linha × coluna; extratores que serializam linha a linha sem reter o cabeçalho produzem sequências de valores sem semântica — por exemplo, `"SP Centro 0.5 1.0 2 3 Rodoviário Não 1.8% R$12,40"`. O modelo não consegue inferir qual campo é o prazo e qual é a taxa. Tabelas com células mescladas (_merged cells_) para agrupamentos regionais são frequentemente quebradas no meio, separando o rótulo `"Região Norte"` dos valores que ele engloba.

**Impacto na qualidade das respostas:** Um atendente que pergunta pelo prazo de entrega para carga fracionada de São Paulo para Manaus entre 50 e 100 kg pode receber uma resposta que confunde dias úteis com dias corridos — porque o retriever encontrou o chunk com os valores corretos, mas o GPT-4o recebeu a linha sem cabeçalho de coluna. No domínio logístico, essa diferença de interpretação gera conflito de SLA documentado, abertura de reclamação formal e eventual crédito de frete indevido.

**Estratégia recomendada:** Utilizar o Azure Document Intelligence (modelo `prebuilt-layout`) para extrair tabelas como objetos estruturados com coordenadas de célula, índices de linha e coluna e flags de _merged cell_. Cada linha da tabela é então serializada como um documento independente com todos os cabeçalhos injetados como prefixo — por exemplo: `"[TABELA: Tabela de Frete Modal Rodoviário] Origem: SP Centro | Destino: AM Manaus | Peso: 50–100 kg | Prazo (dias úteis): 8 | Prazo (dias corridos): 11 | Taxa redespacho: 1,8%"`. A estratégia alternativa de conversão para Markdown (via `pdfplumber` ou `camelot`) é funcional apenas para PDFs nativos com grades bem definidas; em tabelas sem bordas visíveis ou com células mescladas complexas, gera Markdown malformado de forma silenciosa, corrompendo a estrutura relacional sem gerar erro no pipeline.

### 2.2 PDFs Escaneados (SharePoint)

**Desafio:** Documentos escaneados não possuem camada de texto — são imagens rasterizadas. O pipeline depende inteiramente da qualidade do OCR. No domínio logístico, os erros mais críticos são: abreviações de setor (`ANTT`, `RNTRC`, `CTe`, `NF-e`) transcritas como sequências ininteligíveis; tabelas escaneadas com linhas finas ou inclinação de digitalização lidas em ordem incorreta (colunas lidas horizontalmente através de linhas diferentes); e campos numéricos críticos com confusão entre `0/O`, `1/l/I` e vírgula/ponto decimal. Documentos digitalizados abaixo de 150 DPI podem retornar blocos de texto completamente ininteligíveis que são indexados normalmente — os chamados "chunks fantasma".

**Impacto na qualidade das respostas:** Um atendente que consulta o limite de peso por volume conforme a norma NS-047 pode receber uma resposta baseada em uma leitura OCR corrompida (`"l.5OO kg"` em vez de `"1.500 kg"`). O GPT-4o trata o segundo como texto corrompido, ignora-o e responde com base apenas no primeiro trecho encontrado — que pode ser de uma versão anterior do documento. No caso de documentos de segurança de carga com implicações legais e contratuais, uma resposta errada derivada de OCR ruim representa um passivo potencial para a empresa, não apenas uma experiência ruim para o atendente.

**Estratégia recomendada:** Utilizar o modelo `prebuilt-read` do Azure Document Intelligence, que retorna _confidence scores_ por palavra. Implementar filtro de qualidade: chunks com _confidence_ médio abaixo de 0,80 são isolados em coleção separada com metadado `qualidade: baixa`, disponíveis para consulta manual mas excluídos do índice principal de retrieval automático. Complementarmente, criar um dicionário de termos logísticos específicos da NovaTech para pós-processamento OCR (normalização de abreviações conhecidas, correção de padrões numéricos). O critério de corte de chunks deve ser o ponto de queda de _confidence_, não o limite de tokens — garantindo que apenas texto com integridade verificada entre no índice vetorial.

### 2.3 Wiki Confluence

**Desafio:** O Confluence é estruturado como grafo: páginas referenciam outras páginas por meio de macros customizadas (`{include}`, `{excerpt-include}`, `{children}`) e links internos. Na exportação via API REST (formato storage XML ou HTML), o conteúdo das macros não é resolvido — a exportação retorna a tag da macro, não o conteúdo que ela injeta na renderização. Uma página de procedimento operacional que contenha `{include: Política de Devolução Vigente}` resultará em um chunk semanticamente incompleto sem que nenhum erro seja gerado no pipeline. Links internos são exportados como texto literal do _anchor_, perdendo o destino; metadados XML de formatação e âncoras internas sobrevivem como texto literal, poluindo o conteúdo dos chunks.

**Impacto na qualidade das respostas:** Um atendente que pergunta sobre o procedimento correto para registrar uma reclamação de carga avariada pode receber uma resposta que descreve o fluxo geral correto, mas que não consegue responder sobre prazos — porque esses prazos estavam em uma página-filha referenciada via macro `{children}` não resolvida. O GPT-4o, sem a informação no contexto, ou alucina um prazo plausível ou responde de forma evasiva, forçando o atendente a continuar a busca manual. A informação existe na base, mas o pipeline nunca a indexou.

**Estratégia recomendada:** Usar a API REST do Confluence para construir um mapa de dependências entre páginas antes da exportação, resolvendo recursivamente todas as relações `{include}`, `{excerpt-include}` e links internos. Cada chunk deve ser enriquecido com metadados hierárquicos: `page_title`, `parent_page`, `space`, `section`, `last_modified` e `linked_pages[]`. O metadado `linked_pages` permite implementar um segundo estágio de retrieval: se o chunk recuperado na primeira busca referencia outras páginas, o pipeline busca automaticamente um chunk dessas páginas para completar o contexto. O metadado `last_modified` é especialmente relevante porque, quando dois chunks com conteúdo conflitante são recuperados, o GPT-4o pode ser instruído a sinalizar a contradição e indicar qual versão é mais recente.

A estratégia alternativa de exportação por HTML renderizado (via Playwright/Selenium, que resolve macros no cliente) é viável tecnicamente, mas tem custo de manutenção elevado: requer reexecução para todas as 400 páginas a cada atualização mensal, e mudanças na autenticação do Confluence podem quebrar o processo silenciosamente.

### 2.4 Planilhas XLSX com Fórmulas Interdependentes

**Desafio:** Planilhas de referência logística armazenam conhecimento em dois níveis: nos valores calculados das células e na lógica das fórmulas. Um pipeline RAG padrão extrai apenas os valores estáticos no momento da exportação, ignorando as fórmulas completamente. O problema crítico não é de extração — é temporal: planilhas atualizadas mensalmente com valores de entrada variáveis (índice de combustível, tabela ANTT, taxa cambial) produzem valores derivados que mudam; qualquer defasagem entre a atualização da planilha e a reindexação do pipeline resulta em respostas confiantes e precisas sobre dados que já não são mais verdadeiros. Adicionalmente, fórmulas com referências entre abas (`=Aba_Sazonalidade!B12 * Aba_Frete!C8`) geram `#REF!` ou `0` quando a planilha é exportada aba por aba — e esses zeros são indexados como dados válidos.

**Impacto na qualidade das respostas:** Este é o **risco de maior gravidade sistêmica** entre todas as fontes. Um atendente que consulta o valor do seguro obrigatório para uma carga de R$ 80.000 pode receber o valor calculado com base nos inputs do mês anterior. O sistema de faturamento cobra o valor correto e recalculado; a discrepância gera contestação do cliente e perda de confiança na ferramenta logo no início da operação. Diferentemente de um chunk com OCR ruim — que o atendente provavelmente perceberá como corrompido — ou de um link quebrado do Confluence — que gera resposta incompleta, não errada — uma planilha desatualizada indexada corretamente produz o pior tipo de erro possível: respostas semanticamente coerentes e formatadas corretamente, mas factualmente incorretas.

**Estratégia recomendada:** As planilhas não devem alimentar o pipeline RAG diretamente. A cada atualização mensal, um processo automatizado (Azure Logic Apps ou Power Automate) exporta os valores calculados e os transforma em documentos de regras em linguagem natural com metadado de vigência explícito — por exemplo: `"Para cargas com NF entre R$ 50.000 e R$ 100.000 transportadas para a Região Sul, o seguro obrigatório é de 0,3% sobre o valor declarado (vigência: fevereiro/2025)"`. Esses documentos substituem a versão anterior no índice com versionamento explícito. A estratégia alternativa de exportação com OpenPyXL (`data_only=True`) é insuficiente porque não resolve fórmulas com dependências entre abas e não garante que zeros oriundos de referências quebradas sejam distinguidos de zeros legítimos.

---

## 3. Estimativa de Tamanho da Base em Tokens

Esta seção quantifica o volume indexável total da base documental da NovaTech, aplicando critérios por tipo de fonte e um fator de correção para conteúdo não textual.

**Regra de conversão adotada:** 1 token ≈ 0,75 palavras (equivalente a: 1 palavra ≈ 1,333 tokens), compatível com o tokenizador do GPT-4o para português técnico.

### 3.1 Critérios de Estimativa por Fonte

**PDFs (SharePoint):** Documentação corporativa de logística é densa em tabelas, listas numeradas e campos rotulados. Uma página A4 de texto puro chegaria a 400–500 palavras; uma página de manual com gráficos e tabelas fica em torno de 200. Para o mix da NovaTech (manuais de procedimento operacional, tabelas de frete e normas de segurança), adota-se **250 palavras/página** como média conservadora.

**Wiki Confluence:** Páginas wiki tendem a ser mais textuais, com procedimentos em linguagem natural e menor densidade de elementos visuais. Adota-se **1.500 palavras/página**, valor fornecido como premissa da análise.

**Planilhas XLSX:** Planilhas de referência logística são matrizes de valores, não documentos textuais. Uma planilha com 20 linhas × 15 colunas tem aproximadamente 300 células preenchidas; estimando 3 "palavras" por célula em média (cabeçalhos verbosos + valores + unidades), chega-se a ~900 palavras por aba. Descontando células puramente numéricas sem contexto semântico, adota-se **800 palavras/planilha** — refletindo apenas o conteúdo semanticamente útil para indexação. O número de planilhas foi estimado em 50 unidades com base no perfil operacional descrito (tabelas de frete por modal, coeficientes sazonais, multiplicadores por tipo de carga).

### 3.2 Cálculo por Fonte

**Fonte 1 — PDFs (SharePoint)**

| Parâmetro | Valor |
|---|---|
| Número de documentos | 800 |
| Média de páginas por documento | 10 |
| Total de páginas | 8.000 |
| Palavras por página | 250 |
| Total de palavras | 2.000.000 |
| Fator de conversão (÷ 0,75) | × 1,333 |
| **Total de tokens (bruto)** | **~2.667.000** |

**Fonte 2 — Wiki Confluence**

| Parâmetro | Valor |
|---|---|
| Número de páginas | 400 |
| Palavras por página | 1.500 |
| Total de palavras | 600.000 |
| Fator de conversão (÷ 0,75) | × 1,333 |
| **Total de tokens (bruto)** | **~800.000** |

**Fonte 3 — Planilhas XLSX**

| Parâmetro | Valor |
|---|---|
| Número de planilhas | 50 |
| Palavras por planilha | 800 |
| Total de palavras | 40.000 |
| Fator de conversão (÷ 0,75) | × 1,333 |
| **Total de tokens (bruto)** | **~53.000** |

### 3.3 Consolidado Bruto

| Fonte | Total de palavras | Tokens (bruto) | % do total |
|---|---:|---:|---:|
| PDFs — SharePoint | 2.000.000 | ~2.667.000 | 76,9% |
| Wiki — Confluence | 600.000 | ~800.000 | 23,1% |
| Planilhas XLSX | 40.000 | ~53.000 | 1,5% |
| **Subtotal** | **2.640.000** | **~3.520.000** | **100%** |

> **Nota:** As planilhas representam menos de 2% do volume em tokens, confirmando que o risco que elas representam (seção 2.4) é de **qualidade**, não de escala.

### 3.4 Fator de Correção para Conteúdo Não Textual

O fator de correção responde à seguinte pergunta: de todo o conteúdo identificado nas fontes, qual fração é efetivamente texto indexável pelo pipeline RAG?

| Componente | Fonte afetada | Desconto estimado | Racional |
|---|---|---|---|
| Imagens, fluxogramas e diagramas embutidos | PDFs | ~15% das páginas | Manuais de procedimento logístico com fluxogramas de processo e fotos de identificação de carga geram pouco ou nenhum texto via extração padrão |
| Tabelas densas em números sem contexto semântico | PDFs + XLSX | ~10% do conteúdo extraído | Linhas de tabela com apenas valores numéricos sem reconstituição de cabeçalho não contribuem para retrieval semântico |
| Macros não resolvidas e artefatos de exportação | Confluence | ~5% do conteúdo exportado | Tags de macro não renderizadas, metadados XML de formatação e âncoras internas que sobrevivem como texto literal |
| **Fator combinado adotado** | **Todas** | **–30%** | **Fator 0,70** |

O valor 0,70 é conservador sem ser pessimista: projetos com alta proporção de documentos escaneados de baixa qualidade ou planilhas majoritariamente numéricas usariam 0,60; bases predominantemente textuais e bem estruturadas, 0,80. O perfil misto da NovaTech justifica 0,70.

### 3.5 Total Ajustado

| | Tokens |
|---|---:|
| Total bruto | ~3.520.000 |
| Fator de correção | × 0,70 |
| **Total ajustado (tokens indexáveis)** | **~2.464.000** |

Para comunicação com stakeholders: **~2,5 milhões de tokens** de conteúdo efetivamente indexável.

### 3.6 Implicações para Dimensionamento do Índice

> **Nota sobre divergência entre partes da análise:** A Parte 2 utilizou chunks de 400 tokens para estimar o número de chunks no índice (~6.250 chunks); a Parte 3 utilizou 500 tokens por chunk (~5.000 chunks). Os dois números são internamente consistentes, mas partem de premissas de tamanho de chunk diferentes. Adota-se aqui o cenário conservador de **400 tokens por chunk**, resultando em ~6.250 chunks — compatível com as faixas de chunking recomendadas na seção 5. O impacto nas análises de orçamento de contexto da seção 4 é marginal, dado que ambos os tamanhos de chunk resultam em um número total de chunks gerenciável.

| Aspecto | Referência |
|---|---|
| Tamanho típico de chunk (com overlap) | ~400 tokens |
| Número estimado de chunks no índice | ~6.250 chunks |
| Janela de contexto do GPT-4o | 128.000 tokens |
| Chunks que cabem em uma única chamada (teórico) | ~320 chunks |
| Chunks típicos por chamada RAG (prática recomendada) | 5–15 chunks (top-k retrieval) |

O volume de ~6.250 chunks é gerenciável por qualquer solução de vector store enterprise sem necessidade de sharding ou arquitetura distribuída. O Azure AI Search na camada Basic ou Standard S1 suporta esse volume, permitindo que o orçamento do projeto seja concentrado na qualidade do pipeline de ingestão — onde os riscos reais se localizam.

---

## 4. Análise de Orçamento de Contexto por Query

Esta seção analisa como alocar a janela de contexto do GPT-4o (128.000 tokens) por query, levando em conta as restrições cognitivas do modelo, especialmente o efeito _lost in the middle_.

### 4.1 Capacidade Teórica por Query

A decomposição do orçamento de 128.000 tokens por query é:

| Componente | Tokens | % da janela |
|---|---:|---:|
| System prompt + instruções | 2.000 | 1,6% |
| Histórico de conversa (estimativa: 3 turnos) | 1.500 | 1,2% |
| Pergunta do usuário (query atual) | 200 | 0,2% |
| Resposta reservada para o modelo (output) | 1.000 | 0,8% |
| **Orçamento disponível para chunks (contexto RAG)** | **123.300** | **96,3%** |

Com chunks de 400 tokens, a capacidade teórica máxima é de **~308 chunks por query**. Esse número é tecnicamente expressivo, mas operacionalmente irrelevante: enviar 300 chunks ao GPT-4o não é uma estratégia de retrieval — é uma transferência de responsabilidade do retriever para o modelo. A atenção do modelo não é uniforme sobre contextos longos, conforme discutido na seção seguinte.

### 4.2 O Efeito _Lost in the Middle_

O efeito _lost in the middle_ descreve um comportamento mensurável em modelos de linguagem com contexto longo: o GPT-4o recupera com alta fidelidade informações posicionadas no **início** e no **fim** do contexto, e com fidelidade progressivamente menor as informações posicionadas no **meio**. Em testes com 20 ou mais documentos em contexto, a taxa de utilização correta do conteúdo central pode cair significativamente, chegando a ser ignorado em contextos muito longos com perguntas diretas.

Para a NovaTech, isso tem consequência concreta: se o chunk que contém o SLA do cliente Silver estiver na posição 8 de 15 chunks enviados, a probabilidade de o modelo utilizá-lo corretamente é menor do que se estivesse na posição 1 ou 15. Tabelas de frete e SLAs — os conteúdos mais consultados nos 320 chamados diários — são exatamente o tipo de informação que não pode ser degradada por posicionamento inadequado.

| Faixa de chunks (top-k) | Qualidade da resposta | Risco de _lost in the middle_ | Cobertura do índice |
|---|---|---|---|
| 1–3 chunks | Alta precisão, baixa cobertura | Nenhum | ~0,05–0,06% |
| 4–8 chunks | Equilíbrio ótimo para queries simples | Baixo | ~0,06–0,13% |
| **8–12 chunks** | **Equilíbrio ótimo para queries compostas** | **Moderado, gerenciável** | **~0,13–0,19%** |
| 13–20 chunks | Cobertura aumenta, atenção começa a dispersar | Alto no meio | ~0,21–0,32% |
| 20+ chunks | Rendimento marginal decrescente | Crítico | >0,32% |

### 4.3 Ponto de Equilíbrio Recomendado

**Top-k = 8 a 12 chunks como regime padrão**, com posicionamento estratégico obrigatório:

1. **Chunk de maior score de relevância → posição 1** (primeiro no contexto)
2. **Segundo chunk mais relevante → última posição** (âncora final)
3. **Chunks de suporte e contexto complementar → posições intermediárias**

| Parâmetro | Valor recomendado | Justificativa |
|---|---|---|
| Top-k padrão | 8–12 chunks | Cobre queries compostas sem dispersar atenção |
| Top-k para queries simples | 4–6 chunks | Reduz ruído e custo de inferência |
| Top-k máximo permitido | 15 chunks | Limiar acima do qual o risco supera o benefício |
| Tokens de contexto RAG (regime padrão) | 3.200–4.800 tokens | 2,5–3,8% da janela — orçamento conservador e eficiente |
| Tokens de contexto RAG (regime máximo) | 6.000 tokens | 4,7% da janela — ainda seguro |

> A janela larga do GPT-4o (128K tokens) não é uma razão para enviar mais contexto — é uma margem de segurança para histórico de conversa longo e respostas detalhadas. A NovaTech utilizará 3–5% da janela disponível no regime recomendado.

### 4.4 Queries Multi-Dimensionais: Retrieval Composto

Queries que combinam múltiplas dimensões de filtragem simultâneas — como *"Qual é o SLA para uma entrega de carga perigosa na região norte para um cliente Silver?"* — representam o caso mais desafiador do pipeline. Essa query cruza quatro dimensões que provavelmente residem em documentos completamente diferentes:

| Dimensão | Fonte provável | Tipo de chunk esperado |
|---|---|---|
| SLA por tipo de cliente (Silver) | PDF de política comercial ou Wiki Confluence | Tabela de níveis de serviço por tier |
| Regras para carga perigosa (IMDG/ANTT) | PDF de norma de segurança | Texto normativo com restrições e procedimentos |
| Prazos por região (Norte) | Planilha convertida em regras (seção 2.4) | Chunk de regra com faixa geográfica |
| Interseção: carga perigosa + região norte | Provavelmente inexistente como chunk único | Requer inferência cruzada pelo modelo |

A estratégia recomendada é **Query Decomposition + Retrieval Paralelo**:

```
Query: "SLA | carga perigosa | região norte | cliente Silver"
          │
          ▼
   [Decomposição em sub-queries via GPT-4o]
   ┌──────────────────────────────────────┐
   │ Sub-query 1: "SLA cliente Silver"    │
   │ Sub-query 2: "carga perigosa normas" │
   │ Sub-query 3: "prazo região norte"    │
   └──────────────────────────────────────┘
          │
          ▼
   [Retrieval paralelo: top-k=4 por sub-query via Azure AI Search (async)]
          │
          ▼
   [Re-ranking semântico + deduplicação por hash de chunk_id → top 10 únicos]
          │
          ▼
   [Posicionamento estratégico: chunk SLA Silver → posição 1;
    chunk prazo Norte → última posição; demais → posições intermediárias]
          │
          ▼
   [GPT-4o sintetiza resposta com citação de fonte por dimensão]
```

| Etapa | Ferramenta no stack Azure |
|---|---|
| Decomposição da query | GPT-4o com prompt de decomposição |
| Retrieval paralelo (top-k por sub-query) | Azure AI Search (chamadas assíncronas) |
| Re-ranking semântico | Azure AI Search Semantic Ranker |
| Deduplicação | Lógica de aplicação (hash de chunk_id) |
| Posicionamento estratégico | Lógica de montagem do prompt |
| Síntese com citação por dimensão | System prompt com instrução explícita |

**Risco residual — contradição entre chunks:** Quando o SLA de um cliente Silver define 5 dias úteis e a norma de carga perigosa define prazo mínimo de 8 dias, e não existe documento que reconcilie essa contradição, o GPT-4o pode: (a) apresentar os dois valores sem resolver — correto mas frustrante; (b) escolher um valor sem transparência — perigoso; ou (c) sinalizar contradição e recomendar validação humana — comportamento ideal. O system prompt deve instruir explicitamente o modelo a identificar e reportar contradições, incluindo os títulos dos documentos em conflito. Isso transforma um risco de resposta errada em um mecanismo de detecção de gaps de governança documental — problema que a NovaTech já tem hoje.

---

## 5. Estratégia de Chunking Recomendada

O princípio orientador desta seção é que chunking não é uma decisão técnica sobre tamanho de texto — é uma decisão de negócio sobre qual é a **unidade mínima de conhecimento que responde a uma pergunta do atendente**. Cada tipo de fonte tem uma unidade natural diferente; forçar todas as fontes no mesmo molde de "N tokens com overlap fixo" é o anti-padrão mais comum e mais custoso em projetos RAG de domínio especializado.

As três perguntas de referência que norteiam os parâmetros desta seção:
- **P1:** "Qual o SLA para cliente Gold?" → resposta é um valor pontual em uma tabela
- **P2:** "Como calcular frete especial de 600 kg para o Norte?" → resposta é uma regra com múltiplas variáveis
- **P3:** "Posso devolver carga perigosa?" → resposta é um trecho normativo com condições e exceções

### 5.1 PDFs com Tabelas Complexas

**Padrão:** Row-as-chunk com cabeçalho injetado  
**Tamanho do chunk:** 150–300 tokens por linha reconstituída  
**Overlap:** Nenhum entre linhas; cabeçalho repetido em cada chunk como prefixo fixo  
**Critério de corte:** Uma linha da tabela = um chunk. Nunca cortar no meio de uma linha.

**Formato do chunk gerado:**
```
[FONTE: Tabela de SLA Comercial | Documento: politica_sla_v3.pdf | Seção: SLA por Tier]
Tier: Gold | Prazo de entrega padrão: 2 dias úteis | Prazo carga especial: 4 dias úteis |
Prazo para região Norte: 5 dias úteis | Janela de atendimento a reclamações: 24h |
Penalidade por atraso: 2% ao dia sobre o valor do frete
```

**Justificativa:** A pergunta P1 tem sua resposta em uma única linha da tabela de SLA. Se essa linha for fragmentada — separando "Prazo de entrega padrão" de "Penalidade por atraso" em dois chunks com overlap — o retriever pode encontrar apenas metade da informação. O atendente recebe o prazo mas não a penalidade; quando o atraso ocorre, a NovaTech não consegue aplicar a penalidade correta porque a informação estava incompleta. A repetição do cabeçalho em cada chunk é redundante em tokens, mas garante que qualquer chunk recuperado seja semanticamente autossuficiente.

### 5.2 PDFs Escaneados

**Padrão:** Chunking hierárquico por seção com filtro de confiança OCR  
**Tamanho do chunk:** 400–600 tokens por seção identificada  
**Overlap:** 50–80 tokens (1–2 frases) entre chunks consecutivos da mesma seção  
**Critério de corte:** Quebras de seção (títulos e subtítulos detectados pelo OCR) ou, na ausência de estrutura, fim de parágrafo. Nunca cortar no meio de uma lista numerada ou enumeração de condições.  
**Regra de pré-chunking:** Chunks com _confidence_ OCR médio abaixo de 0,80 são isolados com metadado `qualidade: baixa` e excluídos do índice principal.

**Justificativa:** A pergunta P3 encontra sua resposta em uma norma com dependência de contexto local forte: "Exceto nos casos previstos no item 3.2.1" só faz sentido se o item 3.2.1 também estiver no contexto. O overlap de 50–80 tokens captura essa dependência sem duplicar chunks inteiros. O filtro de OCR é crítico porque normas de segurança de carga com texto corrompido podem ser recuperadas por similaridade semântica superficial e enviadas ao GPT-4o, que interpretará valores ilegíveis como dados válidos.

### 5.3 Wiki Confluence

**Padrão:** Chunking semântico por seção com enriquecimento hierárquico de metadados  
**Tamanho do chunk:** 300–500 tokens por seção de página  
**Overlap:** 60–100 tokens entre seções de uma mesma página  
**Critério de corte:** Cabeçalhos de nível H2 ou H3. Nunca cortar no meio de um procedimento numerado (passos 1–N devem permanecer no mesmo chunk, ou o número do passo anterior deve ser repetido como prefixo).

**Metadados obrigatórios em cada chunk:**
```
page_title: "Procedimento de Devolução de Carga"
parent_page: "Manual de Atendimento ao Cliente"
space: "Operações"
section: "Condições para Devolução"
last_modified: "2025-01-15"
linked_pages: ["Tabela de SLA", "Normas de Carga Perigosa"]
```

**Justificativa:** O metadado `linked_pages` habilita um segundo estágio de retrieval: se o chunk recuperado referencia outras páginas, o pipeline busca automaticamente um chunk dessas páginas, resolvendo parcialmente o problema de fragmentação de conhecimento da seção 2.3. O metadado `last_modified` permite que, quando dois chunks conflitantes são recuperados, o GPT-4o identifique qual versão é mais recente — transformando um risco de resposta errada em um indicador de inconsistência documental.

### 5.4 Planilhas XLSX

**Padrão:** Chunk-por-regra gerado a partir de documento intermediário (não da planilha direta)  
**Tamanho do chunk:** 100–200 tokens por regra de negócio  
**Overlap:** Nenhum — cada regra é autossuficiente  
**Critério de corte:** Definido na etapa de conversão: cada linha da planilha que representa uma combinação única de condições gera exatamente um chunk de regra.

**Formato do chunk gerado:**
```
[FONTE: Tabela de Frete Modal Rodoviário | Vigência: fevereiro/2025 | Gerado em: 2025-02-01]
Origem: SP (qualquer município) | Destino: AM (Manaus) | Faixa de peso: 501–1000 kg |
Modal: Rodoviário | Prazo (dias úteis): 9 | Prazo (dias corridos): 13 |
Taxa de frete base: R$ 4,20/kg | Taxa de redespacho: 2,1% | Seguro obrigatório: incluso
```

**Justificativa:** A pergunta P2 requer a combinação exata de três variáveis: peso (600 kg → faixa 501–1000), destino (Norte → região AM/PA/RO) e tipo de carga. Se a planilha for chunked diretamente por bloco de células, o retriever encontra os números corretos mas sem semântica — o GPT-4o não consegue identificar qual coluna é prazo e qual é taxa de redespacho. O metadado de vigência torna explícito quando a regra foi gerada, e o sistema pode alertar o atendente quando o chunk recuperado tem data anterior ao mês atual.

### 5.5 Resumo Consolidado

| Fonte | Padrão de chunking | Tamanho | Overlap | Critério de corte |
|---|---|---|---|---|
| PDFs com tabelas | Row-as-chunk com cabeçalho injetado | 150–300 tokens | Nenhum | Uma linha = um chunk |
| PDFs escaneados | Hierárquico por seção + filtro OCR | 400–600 tokens | 50–80 tokens | Quebra de seção ou fim de parágrafo |
| Wiki Confluence | Semântico por seção + metadados hierárquicos | 300–500 tokens | 60–100 tokens | Cabeçalhos H2/H3; nunca no meio de procedimento numerado |
| Planilhas XLSX | Chunk-por-regra via documento intermediário | 100–200 tokens | Nenhum | Uma combinação de condições = um chunk |

### 5.6 Anti-Padrões a Evitar

Os cinco anti-padrões abaixo foram identificados especificamente para o perfil documental da NovaTech. Cada um tem histórico de causar falhas silenciosas — erros que o pipeline processa sem exceção, mas que produzem respostas incorretas ou incompletas.

**Anti-padrão 1 — Chunking por tamanho fixo aplicado a todas as fontes:** Definir 512 tokens com overlap de 50 e aplicar indiscriminadamente. Uma linha de tabela de frete tem ~80 tokens; um chunk de 512 tokens agregaria 6 linhas de combinações origem-destino-peso no mesmo vetor. O retriever retornará esse chunk para qualquer pergunta de frete; o GPT-4o receberá 6 regras misturadas com 15 colunas cada e terá alta probabilidade de confundir prazos com taxas — exatamente o tipo de erro mais frequente nos 320 chamados diários.

**Anti-padrão 2 — Indexar planilhas XLSX diretamente sem conversão intermediária:** Exportar para CSV e indexar linhas como texto puro. O problema não é de formatação — é temporal. A indexação captura os valores calculados de um determinado mês; quando os inputs mudam no mês seguinte, o índice contém regras desatualizadas sem nenhum sinal de alerta. O atendente usa o assistente em fevereiro, recebe valores de janeiro com total confiança, e a discrepância aparece apenas no faturamento.

**Anti-padrão 3 — Overlap excessivo (>20% do tamanho do chunk) para compensar chunking mal calibrado:** Usar overlaps de 200–300 tokens em chunks de 500 tokens. Com ~6.250 chunks e overlap de 40%, o número de chunks únicos cai para ~3.750, mas o volume de tokens indexados aumenta 40%. Em tabelas de frete, o overlap duplica linhas de dados entre chunks adjacentes; o retriever retorna dois chunks com a mesma linha, e o GPT-4o pode interpretá-la como duas regras distintas ou como uma confirmação artificial que aumenta indevidamente sua confiança num valor que pode estar errado.

**Anti-padrão 4 — Chunks de página inteira para documentos do Confluence:** Páginas do Confluence da NovaTech têm em média 1.500 palavras (~2.000 tokens) — quatro vezes o tamanho recomendado. Um chunk de 2.000 tokens indexado como vetor único terá embedding que representa a "média semântica" de todos os tópicos da página. Quando o atendente pergunta sobre "prazo de reclamação de carga avariada", o retriever pode não retornar esse chunk porque o embedding é dominado pelo tópico principal e a informação sobre prazo tem peso semântico diluído. A informação existe no índice — simplesmente nunca é recuperada.

**Anti-padrão 5 — Ignorar metadados de fonte e data:** Indexar conteúdo sem título do documento, data de criação, área responsável e versão. Sem metadado de data e área responsável, quando dois chunks com conteúdo conflitante são recuperados, o GPT-4o não tem como saber qual é mais recente. Ele sintetiza uma resposta que mistura as duas versões ou escolhe arbitrariamente. Com metadados, o mesmo cenário produz: *"Encontrei duas versões conflitantes: a política comercial de novembro/2024 define 3 dias úteis, enquanto o manual operacional de janeiro/2025 define 5 dias úteis. Recomendo validar com a área de Operações antes de confirmar ao cliente."*

---

## 6. Conclusão e Principais Riscos Técnicos

O pipeline RAG para a NovaTech é tecnicamente viável dentro do prazo e orçamento disponíveis. O volume total indexável (~2,5 milhões de tokens, ~6.250 chunks) é gerenciável sem arquitetura distribuída, o stack Azure cobre os requisitos técnicos identificados, e a integração com Teams/SharePoint é nativa ao ecossistema existente.

A viabilidade, no entanto, é condicionada ao tratamento adequado dos riscos abaixo. Eles foram selecionados por combinarem **alta probabilidade de ocorrência** com **impacto direto na confiança do usuário final** — o critério mais crítico para adoção da ferramenta pela equipe de atendimento.

### Riscos Técnicos Críticos

| # | Risco | Probabilidade | Impacto | Mitigação recomendada |
|---|---|---|---|---|
| R1 | **Desatualização silenciosa do índice após atualização mensal de planilhas** | Alta | Crítico | Implementar processo automatizado (Azure Logic Apps/Power Automate) de conversão planilha → documento de regras com versionamento explícito e data de vigência; adicionar alerta ao atendente quando o chunk recuperado tem data anterior ao mês corrente |
| R2 | **Degradação da qualidade de extração em PDFs com tabelas complexas e células mescladas** | Alta | Alto | Adotar Azure Document Intelligence (`prebuilt-layout`) como extrator principal; implementar validação pós-extração com amostragem de chunks de tabela antes da indexação; não usar extratores baseados em heurísticas de borda como solução primária |
| R3 | **Chunks semanticamente incompletos oriundos de macros não resolvidas no Confluence** | Média-Alta | Alto | Implementar resolução de grafo de dependências via API REST do Confluence antes da exportação; validar cobertura por amostragem de páginas com macros `{include}` e `{excerpt-include}` antes do go-live |
| R4 | **Respostas incorretas derivadas de documentos contraditórios entre versões** | Média | Alto | Instruir explicitamente o GPT-4o no system prompt a identificar e reportar contradições com indicação de fonte e data; incluir `last_modified` e área responsável em todos os metadados de chunk; usar esse mecanismo como instrumento de auditoria documental contínua |
| R5 | **Alucinação a partir de chunks com OCR corrompido de documentos escaneados** | Média | Alto | Implementar filtro de _confidence_ OCR com limiar 0,80; isolar chunks de baixa qualidade em coleção separada fora do fluxo de retrieval automático; priorizar reescaneamento de documentos críticos (normas de segurança de carga) antes da indexação |

> **Nota sobre o risco R1:** É o único com probabilidade **Alta** e impacto **Crítico** simultaneamente. A estratégia de mitigação — conversão para documentos de regras com vigência explícita — precisa estar operacional desde o primeiro ciclo de atualização mensal após o go-live, não pode ser implementada como melhoria iterativa posterior. Sua ausência invalida o contrato de confiabilidade do assistente para o caso de uso mais frequente (consultas de frete e SLA), com impacto direto em disputas comerciais e contestações de faturamento.

---

*Fim do documento — Análise Técnica de Viabilidade — Pipeline RAG NovaTech*