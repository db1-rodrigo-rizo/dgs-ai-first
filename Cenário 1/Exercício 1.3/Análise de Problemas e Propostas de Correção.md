# Análise de Problemas e Propostas de Correção — Pipeline de RAG NovaTech

## Contexto

Os problemas descritos neste documento foram identificados durante a execução dos 5 testes documentados em **Resultados dos Testes.md**. Os testes utilizaram as perguntas do mapa de cobertura do Anexo B como gabarito, permitindo comparar objetivamente os chunks retornados pelo pipeline com os chunks esperados.

O pipeline é tecnicamente funcional: ingere os 5 documentos da NovaTech, gera embeddings com o modelo `all-MiniLM-L6-v2` e realiza busca por similaridade no ChromaDB. Os problemas identificados são de qualidade de retrieval — não de infraestrutura.

---

## Problema 1 — Chunks com conteúdo misto diluem a semântica

**Observado nos testes:** 1 e 2

**Descrição:**

A estratégia de chunking por seção markdown (`##` e `###`) agrupou conteúdo de subseções diferentes num mesmo bloco. O caso mais evidente ocorreu na POL-001: a seção 3.5 (custos de devolução) absorveu texto da seção 3.4 (devoluções parciais) porque ambas estavam sob o mesmo header de nível superior. O chunk resultante contém múltiplos tópicos — custos, proporcionalidade de reembolso, prazo expirado — e seu embedding representa uma média semântica de todo esse conteúdo, não o tópico principal.

Como consequência, no Teste 1 ("Qual é o prazo para devolução?"), este chunk de conteúdo misto ranqueou em primeiro lugar — acima do chunk POL-001 seção 3.1, que contém exatamente o prazo de 7 dias úteis que a pergunta busca. No Teste 2 ("Posso devolver carga perigosa?"), o chunk POL-001 seção 3.2 — que contém a regra de exclusão de cargas perigosas — não apareceu entre os 5 retornados.

**Impacto:**

Em ambos os casos, o chunk mais relevante foi preterido por chunks maiores e semanticamente difusos. Um LLM operando com esses chunks produziria respostas imprecisas ou incorretas, pois a informação crítica simplesmente não estaria presente no contexto.

**Proposta de correção:**

Refinar o chunking para respeitar subseções (`####`) além de seções (`###`), reduzindo a granularidade dos chunks. Adicionalmente, implementar um limite máximo de tokens por chunk — sugestão de 300 tokens. Chunks que ultrapassem esse limite devem ser divididos mesmo na ausência de um novo header, usando quebras de parágrafo como critério secundário de divisão.

---

## Problema 2 — Tabelas fragmentadas linha a linha perdem contexto estrutural

**Observado nos testes:** 3 e 4

**Descrição:**

Tabelas em formato markdown foram divididas em um chunk por linha durante a ingestão. Exemplos observados nos testes:

- Teste 3: a tabela de SLAs gerou chunks individuais como `"Métrica: Gerente de conta dedicado | Gold: Sim | Silver: Não | Standard: Não"` e `"Métrica: Relatório mensal de performance | Gold: Sim (detalhado) | Silver: Sim (resumido) | Standard: Sob demanda"`. As linhas com os tempos de resposta e resolução — a resposta direta à pergunta sobre SLA — não apareceram entre os 5 retornados.
- Teste 4: a tabela de multiplicadores regionais foi igualmente fragmentada, impedindo que "Manaus = região Norte = multiplicador 1.8" fosse recuperado como unidade semântica coerente.

O problema é estrutural: uma linha isolada de tabela tem pouco contexto semântico. O embedding de `"Região: Norte | Multiplicador: 1.8"` não consegue estabelecer conexão com a pergunta "Frete para 600kg para Manaus?" porque o vínculo entre "Manaus" e "região Norte" não está explícito no chunk.

**Impacto:**

Perguntas que dependem de dados tabulares — SLAs, multiplicadores regionais, faixas de peso — produzem retrieval de baixa qualidade. São exatamente os tipos de pergunta mais frequentes no contexto de atendimento ao cliente da NovaTech.

**Proposta de correção:**

Duas abordagens complementares:

1. **Preservar tabelas como unidade indivisível:** durante o chunking, detectar blocos de tabela markdown (sequências de linhas iniciando com `|`) e mantê-los inteiros num único chunk, independentemente do tamanho.

2. **Desnormalizar tabelas em frases durante o pré-processamento:** converter cada linha de tabela em uma frase completa antes da geração de embeddings. Exemplo: `"O SLA de primeira resposta para cliente Gold é de 2 horas úteis."` em vez de `"Tempo de primeira resposta | Gold: Até 2h úteis"`. Frases completas produzem embeddings semanticamente mais ricos e melhoram significativamente o retrieval para perguntas em linguagem natural.

---

## Problema 3 — Ausência de controle de versão causa contradição entre documentos

**Observado nos testes:** 4 e 5

**Descrição:**

O pipeline ingere as duas versões do PROC-042 (v1 de março/2023 e v2 de novembro/2023) sem qualquer distinção de prioridade ou versionamento nos metadados. Nos testes realizados:

- Teste 4: chunks da v1 e da v2 apareceram juntos com fatores de peso contraditórios para a mesma faixa de peso (v1: 1.2 para 1.001–3.000kg; v2: 1.15 para a mesma faixa).
- Teste 5: o multiplicador para o Sudeste apareceu com dois valores diferentes — 1.0 (v1) e 1.1 (v2) — e a versão desatualizada ranqueou em primeiro lugar com score 0.5921 contra 0.5833 da versão atual.

Este problema reflete uma característica real da documentação da NovaTech descrita no Anexo A: ambos os documentos coexistem no SharePoint sem hierarquia formal, e o PROC-042 v1 não foi arquivado após a publicação da v2.

**Impacto:**

Um LLM recebendo chunks contraditórios sem instrução de prioridade pode produzir respostas com valores incorretos — especificamente, usar multiplicadores da versão desatualizada para calcular fretes. Em contexto de atendimento ao cliente, isso representa risco de informar valores errados ao cliente.

**Proposta de correção:**

Duas abordagens complementares:

1. **Enriquecer os metadados de ingestão com versão e data:** durante o processamento dos documentos, extrair e armazenar a data de emissão e o número de versão como campos de metadata no ChromaDB. No momento da busca, implementar um filtro de pós-processamento que, ao identificar dois chunks do mesmo domínio temático (ex: mesmo prefixo de documento — PROC-042), priorize o chunk com data de emissão mais recente.

2. **Separar documentos obsoletos em collection distinta:** criar uma collection `novatech_historico` no ChromaDB para versões anteriores de documentos. O pipeline de produção consulta apenas a collection `novatech` (versões ativas), enquanto a collection histórica fica disponível para consultas específicas de auditoria ou disputas contratuais (onde a versão à época do contrato pode ser relevante).

---

## Observação adicional — Comportamento do LLM ao receber contexto insuficiente

Durante o teste do `pipeline.py`, o prompt completo montado pelo pipeline foi colado no Claude para geração da resposta final. A pergunta utilizada foi "Qual o prazo de devolução para carga perigosa?" — um caso que combina dois domínios (devolução e carga perigosa) e cujo chunk principal (POL-001 seção 3.2) não foi recuperado pelo pipeline.

O Claude não respondeu como NovaTech Assistant. Em vez disso, identificou que estava sendo avaliado e respondeu como analisador do sistema, descrevendo qual deveria ser a resposta correta e por quê. Embora o raciocínio apresentado esteja correto — o modelo identificou que o chunk crítico estava ausente e que o FAQ informal não deveria ser usado como fonte normativa —, este comportamento seria problemático em produção.

Este caso evidencia duas necessidades de melhoria:

1. **No retrieval:** o chunk POL-001-B (seção 3.2) precisa ser recuperado para perguntas sobre devolução de carga perigosa. Sem ele, qualquer resposta do LLM será incompleta ou baseada em fonte não confiável.
2. **No system prompt:** incluir instrução explícita para que o assistente mantenha o papel independentemente do contexto da conversa, impedindo que o modelo "saia do personagem" ao identificar padrões de teste ou avaliação.
