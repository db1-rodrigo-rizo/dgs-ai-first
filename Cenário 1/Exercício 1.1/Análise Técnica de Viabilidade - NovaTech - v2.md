# Análise Técnica de Viabilidade — Pipeline RAG NovaTech

## ANÁLISE TÉCNICA DE VIABILIDADE

**Pipeline RAG — NovaTech**

| **Projeto** | Assistente de IA para Atendimento ao Cliente |
|---|---|
| **Modelo LLM de referência** | GPT-4o (128.000 tokens de janela) |
| **Destinatário** | Tech Lead do Projeto |
| **Revisão** | V2 — Após revisão técnica sênior (correções de premissas, estimativas e riscos) |

---

## 1. Introdução e Contexto do Projeto

A NovaTech é uma empresa de logística com 1.200 funcionários cuja operação depende de um corpus documental extenso e heterogêneo. A equipe de atendimento ao cliente (45 pessoas) processa em média **320 chamados por dia**, dos quais aproximadamente 60% exigem consulta à documentação interna. O tempo médio atual de busca é de **12 minutos por chamado**; a meta estabelecida pela diretoria é reduzir esse indicador para menos de **2 minutos** — uma redução de 83%.

O problema não é apenas de acesso: a documentação está distribuída em três fontes com formatos, ciclos de atualização e responsáveis distintos, sem processo unificado de revisão. Há casos documentados de contradições entre versões, que hoje são resolvidos informalmente. Esse padrão de resolução não escala, não é auditável e é exatamente o que o assistente de IA deve substituir — com a ressalva de que o assistente só poderá ser mais confiável do que o processo atual se o pipeline de ingestão for construído com rigor técnico suficiente para não introduzir novos erros.

### 1.1 Fontes de Dados

| **Fonte** | **Volume** | **Formatos** | **Ciclo de atualização** | **Responsável** |
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

**Desafio**

Tabelas de frete com 15 ou mais colunas perdem sua estrutura relacional quando convertidas para texto plano por extratores PDF convencionais. O significado de uma célula é definido pelo cruzamento linha × coluna; extratores que serializam linha a linha sem reter o cabeçalho produzem sequências de valores sem semântica — por exemplo: "SP Centro 0.5 1.0 2 3 Rodoviário Não 1.8% R$12,40". Tabelas com células mescladas (*merged cells*) para agrupamentos regionais são frequentemente quebradas, separando o rótulo "Região Norte" dos valores que ele engloba.

**Impacto na Qualidade das Respostas**

Um atendente que pergunta pelo prazo de entrega para carga fracionada de São Paulo para Manaus entre 50 e 100 kg pode receber uma resposta que confunde dias úteis com dias corridos. No domínio logístico, essa diferença gera conflito de SLA documentado, abertura de reclamação formal e eventual crédito de frete indevido.

**Estratégia Recomendada**

Utilizar o **Azure Document Intelligence (modelo prebuilt-layout)** para extrair tabelas como objetos estruturados com coordenadas de célula, índices de linha e coluna e flags de merged cell. Cada linha é serializada como documento independente com todos os cabeçalhos injetados como prefixo. A estratégia alternativa de conversão para Markdown é funcional apenas para PDFs nativos com grades bem definidas; em tabelas sem bordas visíveis ou com células mescladas complexas, gera Markdown malformado de forma silenciosa.

### 2.2 PDFs Escaneados (SharePoint)

**Desafio**

Documentos escaneados não possuem camada de texto. O pipeline depende inteiramente da qualidade do OCR. No domínio logístico, os erros mais críticos são: abreviações de setor transcritas como sequências ininteligíveis; tabelas com linhas finas ou inclinação lidas em ordem incorreta; e campos numéricos com confusão entre caracteres visualmente similares (0/O, 1/l/I). Documentos digitalizados abaixo de 150 DPI podem retornar blocos de texto ininteligíveis indexados normalmente — os chamados "chunks fantasma".

**Impacto na Qualidade das Respostas**

Um atendente que consulta o limite de peso por volume conforme a norma NS-047 pode receber uma resposta baseada em leitura OCR corrompida. No caso de documentos de segurança de carga com implicações legais e contratuais, uma resposta errada derivada de OCR ruim representa um passivo potencial para a empresa.

**Estratégia Recomendada**

Utilizar o modelo **prebuilt-read do Azure Document Intelligence**, que retorna confidence scores por palavra. Implementar filtro de qualidade com **limiar provisório de 0,80** — sujeito a calibração na fase de discovery. Procedimento obrigatório: processar amostra de 20 PDFs escaneados representativos, medir a distribuição de confidence scores e identificar o percentil que minimiza simultaneamente falsos positivos (chunks ruins no índice) e falsos negativos (chunks válidos excluídos). Chunks abaixo do limiar calibrado são isolados em coleção separada com metadado `qualidade: baixa`, excluídos do índice principal. Definir SLA para revisão humana dos chunks isolados: documentos de normas de segurança de carga devem ser revisados em até 5 dias úteis após isolamento. Complementarmente, criar dicionário de termos logísticos da NovaTech para pós-processamento OCR. O limiar final pode ser diferente de 0,80 dependendo da distribuição real do corpus.

### 2.3 PDFs Nativos com Texto Corrido (SharePoint)

**Desafio**

PDFs nativos sem tabelas dominantes (manuais, contratos, procedimentos narrativos) representam uma parcela relevante dos ~800 documentos do SharePoint. Não são capturados adequadamente pela estratégia row-as-chunk de 2.1 (projetada para tabelas) nem pelo pipeline OCR de 2.2 (projetado para documentos escaneados sem camada de texto). Aplicar qualquer um desses dois fluxos a documentos de texto corrido resulta em chunking incorreto ou uso desnecessário de créditos do Azure Document Intelligence.

**Impacto na Qualidade das Respostas**

Documentos de texto corrido processados com a estratégia errada produzem chunks truncados no meio de argumentos normativos ou procedimentos sequenciais — exatamente o tipo de fragmentação que destrói o contexto local necessário para responder perguntas do tipo "quais são as condições para X".

**Estratégia Recomendada**

Classificar os PDFs do SharePoint em três categorias antes da ingestão: (a) PDFs com tabelas complexas — fluxo 2.1; (b) PDFs escaneados — fluxo 2.2; (c) PDFs nativos com texto corrido — fluxo desta seção. Critério de classificação automatizável: se o Azure Document Intelligence retornar menos de 10% do conteúdo como células de tabela, o documento cai no fluxo de texto corrido. Nesses casos, utilizar extração de texto nativa do PDF (sem OCR) com chunking hierárquico por seção conforme outline do documento; fallback para quebra por parágrafo quando o outline estiver ausente.

### 2.4 Wiki Confluence

**Desafio**

O Confluence é estruturado como grafo. Na exportação via API REST, o conteúdo das macros (`{include}`, `{excerpt-include}`, `{children}`) não é resolvido — a exportação retorna a tag da macro, não o conteúdo. Uma página de procedimento que contenha `{include: Política de Devolução Vigente}` resultará em chunk semanticamente incompleto sem que nenhum erro seja gerado no pipeline.

**Impacto na Qualidade das Respostas**

Um atendente que pergunta sobre o procedimento para registrar uma reclamação de carga avariada pode receber uma resposta que descreve o fluxo geral correto, mas que não consegue responder sobre prazos — porque esses prazos estavam em uma página-filha referenciada via macro não resolvida.

**Estratégia Recomendada**

Usar a API REST do Confluence para **construir um mapa de dependências entre páginas** antes da exportação, resolvendo recursivamente todas as relações de include e links internos. Cada chunk deve ser enriquecido com metadados hierárquicos: `page_title`, `parent_page`, `space`, `section`, `last_modified`, `linked_pages[]`. O metadado `linked_pages` habilita um segundo estágio de retrieval para completar contexto fragmentado. O metadado `last_modified` permite sinalizar contradições entre versões.

### 2.5 Planilhas XLSX com Fórmulas Interdependentes

**Desafio**

Planilhas de referência logística armazenam conhecimento em dois níveis: nos valores calculados das células e na lógica das fórmulas. Um pipeline RAG padrão extrai apenas os valores estáticos no momento da exportação, ignorando as fórmulas completamente. O problema crítico é temporal: planilhas atualizadas mensalmente com inputs variáveis (índice de combustível, tabela ANTT, taxa cambial) produzem valores derivados que mudam; qualquer defasagem entre atualização e reindexação resulta em respostas confiantes sobre dados desatualizados.

> **Este é o risco de maior gravidade sistêmica entre todas as fontes.** Uma planilha desatualizada indexada corretamente produz o pior tipo de erro possível: respostas semanticamente coerentes e formatadas corretamente, mas factualmente incorretas — diferente de um chunk com OCR ruim (perceptível) ou um link quebrado (resposta incompleta, não errada).

**Impacto na Qualidade das Respostas**

Um atendente que consulta o valor do seguro obrigatório pode receber o valor calculado com base nos inputs do mês anterior. O sistema de faturamento cobra o valor correto recalculado; a discrepância gera contestação do cliente e erosão de confiança na ferramenta logo no início da operação.

**Estratégia Recomendada**

As planilhas **não devem alimentar o pipeline RAG diretamente**. A cada atualização mensal, um processo automatizado (Azure Logic Apps ou Power Automate) exporta os valores calculados e os transforma em **documentos de regras em linguagem natural** com metadado de vigência explícito — por exemplo: "Para cargas com NF entre R$ 50.000 e R$ 100.000 transportadas para a Região Sul, o seguro obrigatório é de 0,3% sobre o valor declarado (vigência: fevereiro/2025)". Esses documentos substituem a versão anterior no índice com versionamento explícito.

**Atenção — cardinalidade combinatória:** Antes da implementação, realizar inventário de cardinalidade por planilha: número de linhas × colunas de condição. Planilhas com mais de 500 combinações devem ser agrupadas por dimensão principal (ex.: origem) e subindexadas por filtro de metadado, não como chunks individuais. A estimativa de chunks totais da seção 3 pressupõe planilhas com baixa cardinalidade combinatória — premissa que precisa ser validada nas primeiras 5 planilhas da amostra de discovery.

---

## 3. Estimativa de Tamanho da Base em Tokens

Esta seção quantifica o volume indexável total da base documental da NovaTech, aplicando critérios por tipo de fonte e um fator de correção para conteúdo não textual. Regra de conversão adotada: **1 token ≈ 0,75 palavras** (1 palavra ≈ 1,333 tokens), compatível com o tokenizador do GPT-4o para português técnico.

> **⚠️ Nota sobre premissas desta seção:** Os valores apresentados a seguir são estimativas de ordem de grandeza baseadas em premissas não validadas empiricamente. A premissa de 250 palavras/página para PDFs, em particular, foi derivada de médias genéricas para documentos de escritório e pode divergir significativamente da composição real do corpus da NovaTech (formulários, contratos e manuais técnicos têm densidades muito distintas). O fator de correção de 30% também é uma estimativa com margem de ±40%. **Ação obrigatória no discovery:** extrair amostra de 30 documentos representativos (10 PDFs nativos, 10 escaneados, 10 com tabelas densas) e substituir as premissas pelos valores medidos antes de qualquer dimensionamento de infraestrutura ou estimativa de custo.

### 3.1 Critérios de Estimativa por Fonte

- **Wiki Confluence:** Páginas mais textuais com menor densidade de elementos visuais. Adota-se **1.500 palavras/página** como premissa da análise.
- **Planilhas XLSX:** Estimativa de **800 palavras/planilha** — refletindo apenas o conteúdo semanticamente útil para indexação (células com cabeçalhos verbosos, valores e unidades), excluindo células puramente numéricas sem contexto. Esta estimativa pressupõe baixa cardinalidade combinatória; planilhas com combinações cruzadas extensas (ex.: 10 origens × 15 destinos × 6 faixas de peso) podem gerar volume de chunks muito superior — veja seção 3.6.

### 3.2 Cálculo por Fonte

**Fonte 1 — PDFs (SharePoint)**

| **Parâmetro** | **Valor** |
|---|---|
| Número de documentos | 800 |
| Média de páginas por documento | 10 |
| Total de páginas | 8.000 |
| Palavras por página | 250 *(premissa não validada — ver nota 3.0)* |
| Total de palavras | 2.000.000 |
| Fator de conversão (÷ 0,75) | × 1,333 |
| **Total de tokens (bruto)** | **~2.667.000** |
| Cenário pessimista (350 pal./pág.) | ~3.700.000 tokens (+39%) |
| Cenário otimista (150 pal./pág.) | ~1.600.000 tokens (−40%) |

**Fonte 2 — Wiki Confluence**

| **Parâmetro** | **Valor** |
|---|---|
| Número de páginas | 400 |
| Palavras por página | 1.500 |
| Total de palavras | 600.000 |
| Fator de conversão (÷ 0,75) | × 1,333 |
| **Total de tokens (bruto)** | **~800.000** |

**Fonte 3 — Planilhas XLSX**

| **Parâmetro** | **Valor** |
|---|---|
| Número de planilhas | 50 |
| Palavras por planilha | 800 |
| Total de palavras | 40.000 |
| Fator de conversão (÷ 0,75) | × 1,333 |
| **Total de tokens (bruto)** | **~53.000** |

### 3.3 Consolidado Bruto

| **Fonte** | **Total de palavras** | **Tokens (bruto)** | **% do total** |
|---|---|---|---|
| PDFs — SharePoint | 2.000.000 | ~2.667.000 | 76,9% |
| Wiki — Confluence | 600.000 | ~800.000 | 23,1% |
| Planilhas XLSX | 40.000 | ~53.000 | 1,5% |
| **Subtotal** | **2.640.000** | **~3.520.000** | **100%** |

> As planilhas representam menos de 2% do volume em tokens, confirmando que o risco que elas representam (seção 2.5) é de qualidade e cardinalidade, não de escala de texto.

### 3.4 Fator de Correção para Conteúdo Não Textual

O fator de correção responde à seguinte pergunta: de todo o conteúdo identificado nas fontes, qual fração é efetivamente texto indexável pelo pipeline RAG?

| **Componente** | **Fonte afetada** | **Desconto est.** | **Racional** |
|---|---|---|---|
| Imagens, fluxogramas e diagramas embutidos | PDFs | ~15% das páginas | Manuais com fluxogramas e fotos de carga geram pouco texto via extração padrão |
| Tabelas densas em números sem contexto semântico | PDFs + XLSX | ~10% do conteúdo | Linhas com apenas valores numéricos sem reconstituição de cabeçalho não contribuem para retrieval semântico |
| Macros não resolvidas e artefatos de exportação | Confluence | ~5% do conteúdo | Tags de macro não renderizadas, metadados XML e âncoras sobrevivem como texto literal |
| **Fator combinado adotado** | **Todas** | **–30%** | **Fator 0,70** |

> **Atenção:** Os três componentes acima não são independentes entre si. Documentos com tabelas densas frequentemente também contêm imagens embutidas, o que pode tornar o desconto cumulativo maior que a soma linear dos percentuais. O fator 0,70 é uma estimativa de ordem de grandeza com margem de ±40% não validada empiricamente. O valor correto será determinado na fase de discovery com amostragem de 50 documentos representativos. Para comunicação com stakeholders, reportar como **"entre 1,5 e 3,5 milhões de tokens indexáveis, com estimativa central de ~2,5M a ser confirmada no discovery"** — e não como um número preciso.

### 3.5 Total Ajustado

| | **Tokens** |
|---|---|
| Total bruto | ~3.520.000 |
| Fator de correção | × 0,70 |
| **Total ajustado (tokens indexáveis)** | **~2.464.000** |

> Para comunicação com stakeholders: ~2,5 milhões de tokens de conteúdo estimadamente indexável — sujeito a validação no discovery (ver nota 3.4).

### 3.6 Implicações para Dimensionamento do Índice

> **Nota sobre divergência entre partes da análise:** a estimativa de chunking usou 400 tokens/chunk (→ ~6.250 chunks) em uma parte e 500 tokens/chunk (→ ~5.000 chunks) em outra. Adota-se o cenário conservador de 400 tokens por chunk (~6.250 chunks). O impacto nas análises de orçamento de contexto é marginal dado que ambos os tamanhos resultam em um volume gerenciável.

> **⚠️ Alerta sobre a estratégia chunk-por-regra (planilhas):** A estimativa de ~6.250 chunks totais pressupõe planilhas com baixa cardinalidade combinatória. Uma única planilha de frete com 10 origens × 15 destinos × 5 faixas de peso × 3 modais gera 2.250 chunks. Com 50 planilhas de perfil similar, o total poderia ultrapassar 50.000–100.000 chunks — invalidando as afirmações de dimensionamento abaixo. **A validação da cardinalidade das planilhas é etapa obrigatória do discovery (semana 1–2) e pré-requisito para qualquer decisão de camada do Azure AI Search.**

| **Aspecto** | **Referência** |
|---|---|
| Tamanho típico de chunk (com overlap) | ~400 tokens |
| Número estimado de chunks no índice | ~6.250 chunks *(sujeito a revisão após validação de cardinalidade — ver alerta acima)* |
| Janela de contexto do GPT-4o | 128.000 tokens |
| Chunks que cabem em uma chamada (teórico) | ~320 chunks |
| Chunks típicos por chamada RAG (prática recomendada) | 5–15 chunks (top-k retrieval) |

Se a contagem de chunks se confirmar na faixa de ~6.250, o volume é gerenciável pelo Azure AI Search nas camadas Basic ou Standard S1, concentrando o orçamento na qualidade do pipeline de ingestão. Se a cardinalidade das planilhas elevar o volume para dezenas de milhares de chunks, a camada e a estratégia de indexação precisam ser reavaliadas.

---

## 4. Análise de Orçamento de Contexto por Query

Esta seção analisa como alocar a janela de contexto do GPT-4o (128.000 tokens) por query, levando em conta as restrições cognitivas do modelo, especialmente o efeito lost in the middle.

### 4.1 Capacidade Teórica por Query

| **Componente** | **Tokens** | **% da janela** |
|---|---|---|
| System prompt + instruções | 2.000 | 1,6% |
| Histórico de conversa (estimativa: 3 turnos) | 1.500 | 1,2% |
| Pergunta do usuário (query atual) | 200 | 0,2% |
| Resposta reservada para o modelo (output) | 1.000 | 0,8% |
| **Orçamento disponível para chunks (contexto RAG)** | **123.300** | **96,3%** |

Com chunks de 400 tokens, a capacidade teórica máxima é de **~308 chunks por query**. Esse número é tecnicamente expressivo, mas operacionalmente irrelevante: enviar 300 chunks ao GPT-4o é uma transferência de responsabilidade do retriever para o modelo. A atenção do modelo não é uniforme sobre contextos longos.

### 4.2 O Efeito Lost in the Middle

O efeito *lost in the middle* descreve um comportamento mensurável: o GPT-4o recupera com alta fidelidade informações posicionadas no **início** e no **fim** do contexto, e com fidelidade progressivamente menor as informações posicionadas no **meio**. Para a NovaTech, isso tem consequência concreta: se o chunk com o SLA do cliente Silver estiver na posição 8 de 15 chunks enviados, a probabilidade de utilização correta é menor do que nas posições extremas.

| **Faixa de chunks (top-k)** | **Qualidade da resposta** | **Risco lost in the middle** | **Cobertura do índice** |
|---|---|---|---|
| 1–3 chunks | Alta precisão, baixa cobertura | Nenhum | ~0,05–0,06% |
| 4–8 chunks | Equilíbrio ótimo para queries simples | Baixo | ~0,06–0,13% |
| 8–12 chunks ★ | Equilíbrio ótimo para queries compostas | Moderado, gerenciável | ~0,13–0,19% |
| 13–20 chunks | Cobertura aumenta, atenção dispersa | Alto no meio | ~0,21–0,32% |
| 20+ chunks | Rendimento marginal decrescente | Crítico | >0,32% |

### 4.3 Ponto de Equilíbrio Recomendado

**Top-k = 8 a 12 chunks como regime padrão**, com posicionamento estratégico obrigatório:

- Chunk de maior score de relevância → posição 1 (primeiro no contexto)
- Segundo chunk mais relevante → última posição (âncora final)
- Chunks de suporte e contexto complementar → posições intermediárias

| **Parâmetro** | **Valor recomendado** | **Justificativa** |
|---|---|---|
| Top-k padrão | 8–12 chunks | Cobre queries compostas sem dispersar atenção |
| Top-k para queries simples | 4–6 chunks | Reduz ruído e custo de inferência |
| Top-k máximo permitido | 15 chunks | Limiar acima do qual o risco supera o benefício |
| Tokens de contexto RAG (regime padrão) | 3.200–4.800 tokens | 2,5–3,8% da janela — orçamento conservador e eficiente |
| Tokens de contexto RAG (regime máximo) | 6.000 tokens | 4,7% da janela — ainda seguro |

> A NovaTech utilizará 3–5% da janela disponível do GPT-4o no regime recomendado. A janela larga (128K tokens) não é uma razão para enviar mais contexto — é uma margem de segurança para histórico de conversa longo e respostas detalhadas.

### 4.4 Queries Multi-Dimensionais: Retrieval Composto

Queries que combinam múltiplas dimensões de filtragem simultâneas representam o caso mais desafiador do pipeline. Exemplo: *"Qual é o SLA para uma entrega de carga perigosa na região norte para um cliente Silver?"* — essa query cruza quatro dimensões que provavelmente residem em documentos completamente diferentes:

| **Dimensão** | **Fonte provável** | **Tipo de chunk esperado** |
|---|---|---|
| SLA por tipo de cliente (Silver) | PDF de política comercial ou Wiki Confluence | Tabela de níveis de serviço por tier |
| Regras para carga perigosa (IMDG/ANTT) | PDF de norma de segurança | Texto normativo com restrições e procedimentos |
| Prazos por região (Norte) | Planilha convertida em regras (seção 2.5) | Chunk de regra com faixa geográfica |
| Interseção: carga perigosa + região norte | Provavelmente inexistente como chunk único | Requer inferência cruzada pelo modelo |

**Estratégia recomendada: Query Decomposition + Retrieval Paralelo**

| **Etapa** | **Ferramenta no stack Azure** |
|---|---|
| Decomposição da query em sub-queries | GPT-4o com prompt de decomposição |
| Retrieval paralelo (top-k=4 por sub-query) | Azure AI Search (chamadas assíncronas) |
| Re-ranking semântico | Azure AI Search Semantic Ranker |
| Deduplicação por hash de chunk_id | Lógica de aplicação |
| Posicionamento estratégico dos chunks | Lógica de montagem do prompt |
| Síntese com citação por dimensão | System prompt com instrução explícita |

**Risco residual — contradição entre chunks:** Quando dois chunks com conteúdo conflitante são recuperados e não existe documento que reconcilie a contradição, o GPT-4o pode apresentar ambos os valores sem resolver, escolher um sem transparência, ou sinalizar a contradição e recomendar validação humana. O system prompt deve instruir explicitamente o modelo a identificar e reportar contradições com indicação de fonte e data — transformando um risco de resposta errada em um mecanismo de detecção de gaps de governança documental.

---

## 5. Estratégia de Chunking Recomendada

O princípio orientador desta seção é que chunking não é uma decisão técnica sobre tamanho de texto — é uma **decisão de negócio sobre qual é a unidade mínima de conhecimento que responde a uma pergunta do atendente**. Cada tipo de fonte tem uma unidade natural diferente; forçar todas as fontes no mesmo molde de "N tokens com overlap fixo" é o anti-padrão mais comum e mais custoso em projetos RAG de domínio especializado.

As três perguntas de referência que norteiam os parâmetros desta seção:

- **P1:** *"Qual o SLA para cliente Gold?"* → resposta é um valor pontual em uma tabela
- **P2:** *"Como calcular frete especial de 600 kg para o Norte?"* → resposta é uma regra com múltiplas variáveis
- **P3:** *"Posso devolver carga perigosa?"* → resposta é um trecho normativo com condições e exceções

### 5.1 PDFs com Tabelas Complexas

| **Parâmetro** | **Valor** |
|---|---|
| Padrão | Row-as-chunk com cabeçalho injetado |
| Tamanho do chunk | 150–300 tokens por linha reconstituída |
| Overlap | Nenhum entre linhas; cabeçalho repetido como prefixo fixo |
| Critério de corte | Uma linha da tabela = um chunk. Nunca cortar no meio de uma linha. |

Formato do chunk gerado:

```
[FONTE: Tabela de SLA Comercial | Documento: politica_sla_v3.pdf | Seção: SLA por Tier]
Tier: Gold | Prazo de entrega padrão: 2 dias úteis | Prazo carga especial: 4 dias úteis |
Prazo para região Norte: 5 dias úteis | Janela de atendimento a reclamações: 24h |
Penalidade por atraso: 2% ao dia sobre o valor do frete
```

**Justificativa (P1):** Se a linha da tabela for fragmentada, o retriever pode encontrar apenas metade da informação. O atendente recebe o prazo mas não a penalidade; quando o atraso ocorre, a NovaTech não consegue aplicar a penalidade correta. A repetição do cabeçalho é redundante em tokens, mas garante que qualquer chunk recuperado seja semanticamente autossuficiente.

### 5.2 PDFs Escaneados

| **Parâmetro** | **Valor** |
|---|---|
| Padrão | Chunking hierárquico por seção com filtro de confiança OCR |
| Tamanho do chunk | 400–600 tokens por seção identificada |
| Overlap | 15% do tamanho do chunk (floor: 50 tokens, cap: 80 tokens) |
| Critério de corte | Quebras de seção (títulos detectados pelo OCR) ou fim de parágrafo. Nunca cortar no meio de lista numerada. |
| Regra de pré-chunking | Chunks com confidence OCR médio < limiar calibrado → isolados com metadado `qualidade: baixa`, excluídos do índice principal |

> **Nota sobre overlap:** Para chunks entre 400–600 tokens, o percentual de 15% resulta em 60–90 tokens de overlap — suficiente para capturar referências cruzadas de parágrafo sem atingir o limiar de redundância do anti-padrão 3 (seção 5.6). A definição em percentual relativo é preferível a valores absolutos porque mantém a proporção independentemente do tamanho real do chunk produzido.

**Justificativa (P3):** Normas com dependência de contexto local forte ("Exceto nos casos previstos no item 3.2.1") requerem overlap para capturar essa dependência. O filtro OCR é crítico porque normas de segurança de carga com texto corrompido podem ser recuperadas por similaridade semântica superficial.

### 5.3 PDFs Nativos com Texto Corrido

| **Parâmetro** | **Valor** |
|---|---|
| Padrão | Chunking hierárquico por seção |
| Tamanho do chunk | 300–500 tokens por seção identificada |
| Overlap | 15% do tamanho do chunk (floor: 50 tokens, cap: 75 tokens) |
| Critério de corte | Quebras H1/H2 detectadas via PDF outline. Fallback: fim de parágrafo. Nunca cortar no meio de lista numerada ou cláusula contratual sequencial. |
| Critério de classificação | Se Azure Document Intelligence retornar < 10% do conteúdo como células de tabela, o documento cai neste fluxo (não no fluxo 5.1). |

**Justificativa:** Documentos como contratos, manuais de procedimento e políticas internas têm estrutura narrativa onde o sentido de um parágrafo depende dos anteriores. O overlap percentual garante continuidade semântica proporcional ao tamanho do chunk produzido. A ausência desta estratégia força o desenvolvedor a uma decisão ad hoc não documentada — o cenário de risco silencioso mais provável em implementações sem cobertura explícita de todos os tipos de fonte.

### 5.4 Wiki Confluence

| **Parâmetro** | **Valor** |
|---|---|
| Padrão | Chunking semântico por seção com enriquecimento hierárquico de metadados |
| Tamanho do chunk | 300–500 tokens por seção de página |
| Overlap | 15% do tamanho do chunk (floor: 60 tokens, cap: 100 tokens) |
| Critério de corte | Cabeçalhos H2 ou H3. Nunca cortar no meio de procedimento numerado. |

Metadados obrigatórios em cada chunk:

```
page_title: "Procedimento de Devolução de Carga"
parent_page: "Manual de Atendimento ao Cliente"
space: "Operações"
section: "Condições para Devolução"
last_modified: "2025-01-15"
linked_pages: ["Tabela de SLA", "Normas de Carga Perigosa"]
```

**Justificativa:** O metadado `linked_pages` habilita um segundo estágio de retrieval para completar contexto fragmentado. O metadado `last_modified` permite que, quando dois chunks conflitantes são recuperados, o GPT-4o identifique qual versão é mais recente.

### 5.5 Planilhas XLSX

| **Parâmetro** | **Valor** |
|---|---|
| Padrão | Chunk-por-regra gerado a partir de documento intermediário (não da planilha direta) |
| Tamanho do chunk | 100–200 tokens por regra de negócio |
| Overlap | Nenhum — cada regra é autossuficiente |
| Critério de corte | Uma combinação única de condições = um chunk, com limite prático de granularidade |

> **Atenção sobre cardinalidade:** Planilhas com mais de 500 combinações (ex.: 10 origens × 15 destinos × 6 faixas de peso) devem ser agrupadas por dimensão principal e subindexadas por filtro de metadado, não como chunks individuais. Realizar inventário de cardinalidade antes de implementar. Ver seção 2.5 e alerta da seção 3.6.

Formato do chunk gerado:

```
[FONTE: Tabela de Frete Modal Rodoviário | Vigência: fevereiro/2025 | Gerado em: 2025-02-01]
Origem: SP (qualquer município) | Destino: AM (Manaus) | Faixa de peso: 501–1000 kg |
Modal: Rodoviário | Prazo (dias úteis): 9 | Prazo (dias corridos): 13 |
Taxa de frete base: R$ 4,20/kg | Taxa de redespacho: 2,1% | Seguro obrigatório: incluso
```

**Justificativa (P2):** A pergunta requer a combinação exata de três variáveis. Se a planilha for chunked diretamente por bloco de células, o GPT-4o não consegue identificar qual coluna é prazo e qual é taxa. O metadado de vigência torna explícito quando a regra foi gerada, e o sistema pode alertar quando o chunk recuperado tem data anterior ao mês atual.

### 5.6 Resumo Consolidado

| **Fonte** | **Padrão de chunking** | **Tamanho** | **Overlap** | **Critério de corte** |
|---|---|---|---|---|
| PDFs com tabelas complexas | Row-as-chunk com cabeçalho injetado | 150–300 tokens | Nenhum | Uma linha = um chunk |
| PDFs escaneados | Hierárquico por seção + filtro OCR | 400–600 tokens | 15% do chunk (50–80 tokens) | Quebra de seção ou fim de parágrafo |
| PDFs nativos (texto corrido) | Hierárquico por seção | 300–500 tokens | 15% do chunk (50–75 tokens) | PDF outline ou fim de parágrafo |
| Wiki Confluence | Semântico por seção + metadados hierárquicos | 300–500 tokens | 15% do chunk (60–100 tokens) | Cabeçalhos H2/H3; nunca no meio de procedimento numerado |
| Planilhas XLSX | Chunk-por-regra via documento intermediário | 100–200 tokens | Nenhum | Uma combinação de condições = um chunk (com limite de cardinalidade) |

### 5.7 Anti-Padrões a Evitar

Os cinco anti-padrões abaixo foram identificados especificamente para o perfil documental da NovaTech. Cada um tem histórico de causar falhas silenciosas — erros que o pipeline processa sem exceção, mas que produzem respostas incorretas ou incompletas.

**Anti-padrão 1 — Chunking por tamanho fixo aplicado a todas as fontes**

*O que é:* Definir 512 tokens com overlap de 50 e aplicar indiscriminadamente a todos os documentos.

*Por que é problemático aqui:* Uma linha de tabela de frete tem ~80 tokens; um chunk de 512 tokens agregaria 6 linhas de combinações origem-destino-peso no mesmo vetor. O retriever retornará esse chunk para qualquer pergunta de frete; o GPT-4o receberá 6 regras misturadas com 15 colunas cada e terá alta probabilidade de confundir prazos com taxas — exatamente o tipo de erro mais frequente nos 320 chamados diários.

**Anti-padrão 2 — Indexar planilhas XLSX diretamente sem conversão intermediária**

*O que é:* Exportar para CSV e indexar linhas como texto puro.

*Por que é problemático aqui:* O problema não é de formatação — é temporal. A indexação captura os valores calculados de um determinado mês; quando os inputs mudam no mês seguinte, o índice contém regras desatualizadas sem nenhum sinal de alerta. O atendente usa o assistente em fevereiro, recebe valores de janeiro com total confiança, e a discrepância aparece apenas no faturamento.

**Anti-padrão 3 — Overlap excessivo (>20% do tamanho do chunk)**

*O que é:* Usar overlaps de 200–300 tokens em chunks de 500 tokens para "garantir" que nenhum contexto seja perdido.

*Por que é problemático aqui:* Com ~6.250 chunks e overlap de 40%, o número de chunks únicos cai, mas o volume de tokens indexados aumenta 40%. Em tabelas de frete, o overlap duplica linhas de dados entre chunks adjacentes; o retriever retorna dois chunks com a mesma linha, e o GPT-4o pode interpretá-la como duas regras distintas ou como confirmação artificial que aumenta indevidamente a confiança num valor errado.

**Anti-padrão 4 — Chunks de página inteira para documentos do Confluence**

*O que é:* Tratar cada página wiki como um único chunk, indexando seu conteúdo completo como vetor único.

*Por que é problemático aqui:* Páginas do Confluence da NovaTech têm em média 1.500 palavras (~2.000 tokens) — quatro vezes o tamanho recomendado. O embedding de um chunk de 2.000 tokens representa a "média semântica" de todos os tópicos da página; a informação sobre prazos de reclamação tem peso semântico diluído pelo tópico principal e nunca é recuperada.

**Anti-padrão 5 — Ignorar metadados de fonte e data**

*O que é:* Indexar conteúdo sem título do documento, data de criação, área responsável e versão.

*Por que é problemático aqui:* A NovaTech tem documentos que se contradizem entre versões. Sem metadados, o GPT-4o não tem como saber qual versão é mais recente e sintetiza uma resposta que mistura as duas versões ou escolhe arbitrariamente. Com metadados, o mesmo cenário produz: *"Encontrei duas versões conflitantes: a política comercial de novembro/2024 define 3 dias úteis, enquanto o manual operacional de janeiro/2025 define 5 dias úteis. Recomendo validar com a área de Operações antes de confirmar ao cliente."*

---

## 6. Conclusão e Principais Riscos Técnicos

O pipeline RAG para a NovaTech é **tecnicamente viável**, com a ressalva de que o prazo de 3 meses é apertado para a complexidade identificada. Uma decomposição preliminar de marcos sugere:

- **Mês 1 — Discovery e validação de premissas:** amostragem de 30+ documentos para calibrar premissas de densidade (palavras/página), classificação de PDFs nos três fluxos, resolução de macros Confluence, inventário de cardinalidade de planilhas, calibração do limiar OCR. Qualquer atraso nesta fase comprime diretamente o tempo de testes — o risco de schedule mais provável.
- **Mês 2 — Construção dos pipelines de ingestão:** implementação das estratégias de chunking por fonte, validação de qualidade de chunks por amostragem, construção do processo automatizado para planilhas (Power Automate/Logic Apps).
- **Mês 3 — Integração e go-live:** integração Teams/SharePoint, testes de aceitação com cenários representativos dos 320 chamados diários, shadow mode (ver risco R7 abaixo) e go-live.

A viabilidade no prazo pressupõe que as premissas de volume e complexidade sejam confirmadas nas primeiras duas semanas. O volume total indexável (~2,5 milhões de tokens, ~6.250 chunks — sujeito a validação de cardinalidade) é potencialmente gerenciável sem arquitetura distribuída, o stack Azure cobre os requisitos técnicos identificados, e a integração com Teams/SharePoint é nativa ao ecossistema existente.

A viabilidade, no entanto, é condicionada ao tratamento adequado dos riscos abaixo. Eles foram selecionados por combinarem alta probabilidade de ocorrência com impacto direto na confiança do usuário final — o critério mais crítico para adoção da ferramenta pela equipe de atendimento.

| **#** | **Risco** | **Probabilidade** | **Impacto** | **Mitigação recomendada** |
|---|---|---|---|---|
| R1 | Desatualização silenciosa do índice após atualização mensal de planilhas | **Alta** | **Crítico** | Implementar processo automatizado (Azure Logic Apps/Power Automate) de conversão planilha → documento de regras com versionamento explícito e data de vigência; alertar o atendente quando o chunk recuperado tem data anterior ao mês corrente |
| R2 | Degradação da qualidade de extração em PDFs com tabelas complexas e células mescladas | Alta | Alto | Adotar Azure Document Intelligence (prebuilt-layout) como extrator principal; implementar validação pós-extração com amostragem de chunks de tabela antes da indexação |
| R3 | Chunks semanticamente incompletos oriundos de macros não resolvidas no Confluence | Média-Alta | Alto | Implementar resolução de grafo de dependências via API REST do Confluence antes da exportação; validar cobertura por amostragem de páginas com macros {include} antes do go-live |
| R4 | Respostas incorretas derivadas de documentos contraditórios entre versões | Média | Alto | Instruir GPT-4o no system prompt a identificar e reportar contradições com indicação de fonte e data; incluir last_modified e área responsável em todos os metadados de chunk |
| R5 | Alucinação a partir de chunks com OCR corrompido de documentos escaneados | Média | Alto | Implementar filtro de confidence OCR com limiar calibrado (provisório: 0,80); isolar chunks de baixa qualidade fora do fluxo de retrieval automático; priorizar reescaneamento de normas de segurança de carga; definir SLA de revisão humana para chunks isolados |
| R6 | Ausência de estratégia de delta ingestion para atualizações incrementais | **Alta** | **Alto** | Definir política de versionamento por documento: cada chunk carrega `document_id` + `version_hash`; na reindexação, chunks com mesmo `document_id` e hash diferente substituem os anteriores (hard delete + reinsert). Documentos removidos da fonte devem ser detectados por comparação de manifesto e expurgados do índice. Sem essa política, o índice acumula versões conflitantes ao longo do tempo de forma estrutural |
| R7 | Abandono da ferramenta por atendentes após primeiros erros visíveis | Alta | Alto | Operar em shadow mode por 2 semanas pós-go-live (assistente responde em paralelo, atendente valida antes de usar); implementar mecanismo de feedback inline por resposta; definir previamente com o Product Owner o percentual de respostas incorretas em 30 dias que justifica pausar a operação. Esses parâmetros devem ser acordados antes do início do desenvolvimento |

> **Nota sobre o risco R1:** é o único com probabilidade Alta e impacto Crítico simultaneamente. A estratégia de mitigação — conversão para documentos de regras com vigência explícita — precisa estar operacional desde o primeiro ciclo de atualização mensal após o go-live, não pode ser implementada como melhoria iterativa posterior. Sua ausência invalida o contrato de confiabilidade do assistente para o caso de uso mais frequente (consultas de frete e SLA), com impacto direto em disputas comerciais e contestações de faturamento.

> **Nota sobre o risco R6:** sem delta ingestion com controle de versão, a mitigação do R4 (contradições via system prompt) se torna insuficiente — o problema deixa de ser pontual e passa a ser estrutural e crescente com cada ciclo mensal de atualização. R6 e R4 são dependentes; R6 deve ser tratado como pré-requisito arquitetural, não como melhoria posterior.

---

*Confidencial — Uso interno*
