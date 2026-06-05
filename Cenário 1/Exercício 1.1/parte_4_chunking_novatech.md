# Estratégia de Chunking Recomendada — Pipeline RAG NovaTech
**Projeto:** Assistente de IA para Atendimento ao Cliente  
**Seção:** Parte 4 — Estratégia de Chunking  
**Base:** Partes 1, 2 e 3 desta análise

---

## Princípio orientador desta seção

Chunking não é uma decisão técnica sobre tamanho de texto — é uma decisão de negócio sobre *qual é a unidade mínima de conhecimento que responde a uma pergunta do atendente*. Cada tipo de fonte da NovaTech tem uma unidade natural diferente, e forçar todas elas no mesmo molde de "N tokens com overlap fixo" é o anti-padrão mais comum e mais caro em projetos RAG de domínio especializado.

As três perguntas de referência usadas nesta análise:

- **P1:** "Qual o SLA para cliente Gold?" → resposta é um valor pontual em uma tabela
- **P2:** "Como calcular frete especial de 600kg para o Norte?" → resposta é uma regra com múltiplas variáveis
- **P3:** "Posso devolver carga perigosa?" → resposta é um trecho normativo com condições e exceções

Cada uma dessas perguntas exige um tipo diferente de chunk. Um sistema com estratégia única falha em pelo menos duas das três.

---

## 1. PDFs com Tabelas Complexas (tabelas de frete, SLAs, políticas comerciais)

### Estratégia recomendada

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

**Justificativa baseada no domínio:**

A pergunta P1 ("Qual o SLA para cliente Gold?") tem uma resposta que vive em uma única linha de uma tabela de SLA. Se essa linha for fragmentada — por exemplo, separando "Prazo de entrega padrão" de "Penalidade por atraso" em dois chunks com overlap — o retriever pode encontrar apenas metade da informação e o GPT-4o responderá parcialmente sem perceber que há dados faltando. O atendente recebe o prazo mas não a penalidade, informa o prazo ao cliente, e quando o atraso ocorre a NovaTech não consegue aplicar a penalidade correta porque o atendente não tinha a informação completa.

A repetição do cabeçalho em cada chunk é redundante em termos de tokens, mas é o que garante que qualquer chunk recuperado pelo retriever seja semanticamente autossuficiente — o modelo não precisa de outro chunk para interpretar os valores.

---

## 2. PDFs Escaneados (normas operacionais, certificados, procedimentos legados)

### Estratégia recomendada

**Padrão:** Chunking hierárquico por seção + filtro de confiança OCR  
**Tamanho do chunk:** 400–600 tokens por seção identificada  
**Overlap:** 50–80 tokens (1–2 frases) entre chunks consecutivos de uma mesma seção  
**Critério de corte:** Cortar em quebras de seção (títulos, subtítulos detectados pelo OCR) ou, na ausência de estrutura clara, em fim de parágrafo. Nunca cortar no meio de uma lista numerada ou enumeração de condições.

**Regra adicional de pré-chunking:** Chunks derivados de trechos com confidence OCR médio abaixo de 0,80 são isolados em uma coleção separada marcada com metadado `qualidade: baixa` e não alimentam o índice principal. Eles ficam disponíveis para consulta manual mas não são retornados automaticamente.

**Justificativa baseada no domínio:**

A pergunta P3 ("Posso devolver carga perigosa?") provavelmente encontra sua resposta em uma norma operacional que define condições, exceções e procedimentos em linguagem regulatória. Esse tipo de conteúdo tem dependência de contexto local forte: "Exceto nos casos previstos no item 3.2.1" só faz sentido se o item 3.2.1 também estiver no contexto. O overlap de 50–80 tokens captura essa dependência sem duplicar chunks inteiros.

O filtro de confiança OCR é crítico aqui porque um chunk de norma de segurança com texto corrompido pode ser recuperado pelo retriever (o embedding ainda captura proximidade semântica parcial) e enviado ao GPT-4o, que vai tentar interpretar valores ilegíveis como `"1.5OO kg"` como dados válidos. No domínio logístico, normas de segurança de carga têm implicações legais — uma resposta errada derivada de OCR ruim não é só uma experiência ruim para o atendente, é um passivo potencial para a empresa.

---

## 3. Wiki do Confluence (procedimentos, políticas, fluxos de atendimento)

### Estratégia recomendada

**Padrão:** Chunking semântico por seção + enriquecimento hierárquico de metadados  
**Tamanho do chunk:** 300–500 tokens por seção de página  
**Overlap:** 60–100 tokens entre seções de uma mesma página (captura transições de contexto)  
**Critério de corte:** Cortar em cabeçalhos de nível H2 ou H3. Nunca cortar no meio de um procedimento numerado (passos 1–N devem permanecer no mesmo chunk ou ter o número do passo anterior repetido como prefixo).

**Metadados obrigatórios em cada chunk:**

```
page_title: "Procedimento de Devolução de Carga"
parent_page: "Manual de Atendimento ao Cliente"
space: "Operações"
section: "Condições para Devolução"
last_modified: "2025-01-15"
linked_pages: ["Tabela de SLA", "Normas de Carga Perigosa"]
```

**Justificativa baseada no domínio:**

O Confluence da NovaTech tem estrutura de grafo — uma página de procedimento faz referência à tabela de SLA, que faz referência à norma de carga perigosa. Quando o atendente faz a pergunta P3 ("Posso devolver carga perigosa?"), a resposta está distribuída: a página de procedimento de devolução diz "sim, conforme condições da norma NS-047", e a norma NS-047 define quais são essas condições.

O metadado `linked_pages` permite que o pipeline implemente um segundo estágio de retrieval: se o chunk recuperado na primeira busca contém referências a outras páginas, o pipeline busca automaticamente um chunk dessas páginas para completar o contexto. Isso resolve parcialmente o problema de fragmentação de conhecimento identificado na Parte 1 sem precisar indexar páginas inteiras como chunks únicos (o que prejudicaria a precisão do retriever).

O metadado `last_modified` é particularmente importante para a NovaTech porque a documentação é atualizada mensalmente por três áreas sem processo unificado. Quando dois chunks recuperados têm datas diferentes e conteúdo conflitante, o GPT-4o pode ser instruído a sinalizar a contradição e indicar qual versão é mais recente.

---

## 4. Planilhas XLSX (tabelas de referência de frete, coeficientes, faixas de peso)

### Estratégia recomendada

**Padrão:** Chunk-por-regra gerado a partir de documento intermediário (não da planilha direta)  
**Tamanho do chunk:** 100–200 tokens por regra de negócio  
**Overlap:** Nenhum — cada regra é autossuficiente  
**Critério de corte:** A unidade de corte não é definida no momento do chunking, mas na etapa de conversão: cada linha da planilha que representa uma combinação única de condições vira exatamente um chunk de regra.

**Formato do chunk gerado (conforme estratégia A da Parte 1):**

```
[FONTE: Tabela de Frete Modal Rodoviário | Vigência: fevereiro/2025 | Gerado em: 2025-02-01]
Origem: SP (qualquer município) | Destino: AM (Manaus) | Faixa de peso: 501–1000 kg |
Modal: Rodoviário | Prazo (dias úteis): 9 | Prazo (dias corridos): 13 |
Taxa de frete base: R$ 4,20/kg | Taxa de redespacho: 2,1% | Seguro obrigatório: incluso
```

**Justificativa baseada no domínio:**

A pergunta P2 ("Como calcular frete especial de 600kg para o Norte?") requer a combinação exata de três variáveis: peso (600kg → faixa 501–1000), destino (Norte → região AM/PA/RO/etc.) e tipo de carga (especial → modal e taxa específicos). Se a planilha for chunked diretamente por bloco de células sem reconstituição de contexto, o retriever encontrará um chunk com os números corretos mas sem semântica — o GPT-4o não conseguirá identificar qual coluna é o prazo e qual é a taxa de redespacho.

A conversão para chunks de regra em linguagem estruturada (etapa realizada mensalmente junto com a atualização da planilha) garante que cada chunk seja uma afirmação completa e verificável. O metadado de vigência torna explícito quando a regra foi gerada, e o sistema pode alertar o atendente quando o chunk recuperado tem data de vigência anterior ao mês atual.

---

## 5. O Que NÃO Fazer — Anti-padrões Específicos para a NovaTech

### Anti-padrão 1: Chunking por tamanho fixo de tokens aplicado a todas as fontes

**O que é:** Definir um tamanho único (ex: 512 tokens com overlap de 50) e aplicar a todos os documentos indiscriminadamente, usando apenas contagem de tokens como critério de corte.

**Por que é problemático aqui:** Uma linha de tabela de frete tem 80 tokens. Um chunk de 512 tokens vai agregar 6 linhas diferentes de combinações origem-destino-peso no mesmo vetor. O retriever vai encontrar esse chunk para qualquer pergunta de frete — mas o GPT-4o vai receber 6 regras misturadas e terá que inferir qual se aplica à pergunta. Com 15 colunas por linha, a chance de confusão entre variáveis (prazo vs. taxa, dias úteis vs. corridos) é alta o suficiente para gerar erros sistemáticos nas respostas sobre prazos de entrega — exatamente o tipo de informação que os 320 chamados diários da NovaTech mais consultam.

---

### Anti-padrão 2: Indexar planilhas XLSX diretamente sem conversão intermediária

**O que é:** Exportar as planilhas para CSV e indexar as linhas como texto puro, ou usar uma biblioteca como OpenPyXL para extrair células e montar chunks a partir dos valores raw.

**Por que é problemático aqui:** Planilhas de frete da NovaTech são atualizadas mensalmente com novos valores de input (índice de combustível, tabela ANTT). Se a indexação captura os valores calculados de uma planilha de janeiro e em fevereiro os inputs mudam, o índice passa a conter regras desatualizadas — e o pipeline não tem como detectar isso automaticamente. Um atendente que usa o assistente em fevereiro recebe valores de janeiro com total confiança, porque o chunk parece correto em formato e estrutura. A discrepância só aparece quando o sistema de faturamento cobra um valor diferente do que o assistente informou, gerando contestação do cliente e perda de confiança na ferramenta logo no início da operação.

---

### Anti-padrão 3: Overlap excessivo (>20% do tamanho do chunk) para compensar chunking mal calibrado

**O que é:** Usar overlaps de 200–300 tokens em chunks de 500 tokens como estratégia de "garantia" de que nenhum contexto seja perdido entre chunks adjacentes.

**Por que é problemático aqui:** Com ~5.000 chunks no índice e overlap de 40%, o número efetivo de chunks únicos cai para ~3.000, mas o volume de tokens indexados aumenta em 40%. Mais grave: em documentos com tabelas de frete, o overlap vai duplicar linhas de dados entre chunks adjacentes. O retriever pode retornar dois chunks diferentes que contêm a mesma linha de tabela — e o GPT-4o, recebendo a mesma informação duas vezes em posições diferentes do contexto, pode interpretá-la como duas regras diferentes ou como uma confirmação que aumenta artificialmente sua confiança em um valor que pode estar errado. O overlap é uma ferramenta para preservar contexto narrativo entre parágrafos, não para compensar chunking que não respeitou as fronteiras naturais do conteúdo.

---

### Anti-padrão 4: Chunks de página inteira para documentos do Confluence

**O que é:** Tratar cada página wiki como um único chunk, indexando seu conteúdo completo como um vetor único.

**Por que é problemático aqui:** Páginas do Confluence da NovaTech têm em média 1.500 palavras (~2.000 tokens) — quatro vezes o tamanho recomendado de chunk. Um chunk de 2.000 tokens indexado como vetor único vai ter um embedding que representa a "média semântica" de todos os tópicos da página. Quando o atendente pergunta sobre "prazo de reclamação de carga avariada", o retriever pode não retornar esse chunk porque o embedding da página inteira é dominado pelo tópico principal (ex: "procedimento geral de devolução") e a informação sobre prazo de reclamação tem peso semântico diluído. A informação existe no índice, mas nunca é recuperada — o assistente responde que não encontrou informação sobre prazos de reclamação, e o atendente volta a perguntar para o colega, exatamente o comportamento que o projeto quer eliminar.

---

### Anti-padrão 5: Ignorar metadados de fonte e data nos chunks

**O que é:** Indexar o conteúdo dos chunks sem metadados estruturados (título do documento, data de criação, área responsável, versão), confiando apenas na similaridade semântica para retrieval.

**Por que é problemático aqui:** A NovaTech tem documentos que se contradizem entre versões — problema explicitamente relatado pela equipe. Sem metadado de data e área responsável, quando dois chunks com conteúdo conflitante são recuperados, o GPT-4o não tem como saber qual é o mais recente nem quem é a fonte de autoridade. Ele vai sintetizar uma resposta que mistura as duas versões ou escolher arbitrariamente uma delas. O atendente recebe uma resposta que parece coerente, age com base nela, e só descobre o problema quando o cliente contesta. Com metadados, o mesmo cenário produz uma resposta como: *"Encontrei duas versões conflitantes sobre este prazo: a política comercial de novembro/2024 define 3 dias úteis, enquanto o manual operacional de janeiro/2025 define 5 dias úteis. Recomendo validar com a área de Operações antes de confirmar ao cliente"* — o que é infinitamente mais útil e transforma o assistente em um detector de inconsistências documentais.

---

## Resumo Consolidado

| Fonte | Padrão de chunking | Tamanho | Overlap | Critério de corte |
|---|---|---|---|---|
| PDFs com tabelas | Row-as-chunk com cabeçalho injetado | 150–300 tokens | Nenhum (cabeçalho repetido) | Uma linha = um chunk |
| PDFs escaneados | Hierárquico por seção + filtro OCR | 400–600 tokens | 50–80 tokens | Quebra de seção ou fim de parágrafo |
| Wiki Confluence | Semântico por seção + metadados hierárquicos | 300–500 tokens | 60–100 tokens | Cabeçalhos H2/H3; nunca no meio de procedimento numerado |
| Planilhas XLSX | Chunk-por-regra via documento intermediário | 100–200 tokens | Nenhum | Uma combinação de condições = um chunk |