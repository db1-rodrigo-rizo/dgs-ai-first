# Análise Técnica de Fontes de Dados — Pipeline RAG NovaTech
**Projeto:** Assistente de IA para Atendimento ao Cliente  
**Seção:** Parte 1 — Análise Técnica de Fontes de Dados  
**Modelo LLM:** GPT-4o  
**Setor:** Logística  

---

## 1. PDFs com Tabelas Complexas (15+ colunas)

### Desafio específico para o pipeline de RAG

Tabelas de frete com 15 ou mais colunas — tipicamente combinando variáveis como região de origem, região de destino, tipo de carga, peso mínimo, peso máximo, prazo em dias úteis, prazo em dias corridos, modal, seguro obrigatório, taxa de redespacho e coeficientes de ajuste sazonal — perdem sua estrutura relacional quando convertidas para texto plano por extratores PDF convencionais (PyMuPDF, pdfplumber, Azure Document Intelligence no modo padrão).

O problema central é que o significado de uma célula é definido pelo cruzamento de dois eixos: a linha (o caso de uso) e a coluna (o atributo). Quando o extrator serializa a tabela linha a linha sem reter o cabeçalho, o chunk resultante se torna algo como `"SP Centro 0.5 1.0 2 3 Rodoviário Não 1.8% R$12,40"` — uma sequência de valores sem semântica. O modelo não consegue inferir que `1.8%` é a taxa de redespacho e não o coeficiente de seguro, porque o cabeçalho ficou em um chunk diferente ou foi descartado.

### Como isso afeta a qualidade das respostas

Um atendente pergunta: *"Qual o prazo de entrega para carga fracionada de São Paulo para Manaus, entre 50 e 100 kg?"*. O retriever encontra o chunk com os valores numéricos corretos, mas o GPT-4o recebe a linha sem os cabeçalhos de coluna. Ele pode confundir a coluna de prazo em dias úteis com a de dias corridos — e entregar ao cliente uma promessa de 5 dias quando a regra é 8. No contexto de logística, essa diferença gera conflito de SLA documentado, abertura de reclamação formal e eventual crédito de frete indevido.

Além disso, tabelas com fusão de células (merged cells) para grupos de regiões são frequentemente quebradas no meio, separando a label `"Região Norte"` dos valores que ela engloba. O modelo então responde com dados de outra faixa geográfica sem perceber a dissociação.

### Estratégias de tratamento

**Estratégia A — Extração estruturada com reconstituição de cabeçalho por chunk** ⭐ *Estratégia mais indicada*

Utilizar Azure Document Intelligence (modelo `prebuilt-layout`) para extrair tabelas como objetos estruturados com coordenadas de célula, índices de linha e coluna, e flags de merged cell. Em seguida, serializar cada linha da tabela como um documento independente no formato `"[TABELA: Tabela de Frete Modal Rodoviário] Origem: SP Centro | Destino: AM Manaus | Peso: 50–100 kg | Prazo (dias úteis): 8 | Prazo (dias corridos): 11 | Taxa redespacho: 1,8%"`.

**Impacto no chunking:** sim, altera fundamentalmente a estratégia. Cada linha da tabela vira um chunk autônomo e semanticamente completo, com todos os cabeçalhos injetados como prefixo. Isso garante que o retriever possa encontrar a combinação exata de atributos e que o GPT-4o receba contexto suficiente para responder com precisão. O custo é um volume maior de chunks, mas com retrieval de altíssima precisão para consultas de frete.

**Estratégia B — Conversão para Markdown com validação pós-extração**

Converter a tabela para formato Markdown estruturado (pipe tables) e chunkar por seção semântica, mantendo o cabeçalho repetido a cada N linhas. Ferramentas como `pdfplumber` com heurísticas de detecção de bordas ou `camelot` conseguem resultados razoáveis em PDFs nativos com grades bem definidas.

**Impacto no chunking:** sim, requer chunking especializado por tabela (não por caractere ou parágrafo). A limitação é que PDFs com tabelas sem bordas visíveis (apenas espaçamento) ou com células mescladas complexas geram Markdown malformado, o que destrói a estrutura relacional silenciosamente — o pipeline processa sem erro, mas com dados corrompidos.

---

## 2. PDFs Escaneados (OCR Necessário)

### Desafio específico para o pipeline de RAG

Documentos escaneados são imagens rasterizadas sem camada de texto. O pipeline de RAG depende inteiramente da qualidade do OCR para ter qualquer texto indexável. No contexto da NovaTech, isso provavelmente inclui manuais operacionais mais antigos, formulários de procedimento preenchidos à mão, certificados de conformidade e normas de segurança de carga digitalizadas de versões impressas.

O problema técnico principal não é simplesmente "o OCR erra palavras". É que o OCR de documentos logísticos enfrenta desafios específicos: abreviações de setor (`ANTT`, `RNTRC`, `CTe`, `MDFe`, `NF-e`) são frequentemente transcritas como sequências de caracteres sem sentido (`ANTî`, `RNTRç`); tabelas escaneadas com linhas finas ou inclinação de digitalização geram texto em ordem de leitura incorreta (colunas lidas da esquerda para a direita atravessando linhas diferentes); e campos numéricos críticos como pesos e valores monetários sofrem confusão entre `0/O`, `1/l/I` e vírgula/ponto decimal.

### Como isso afeta a qualidade das respostas

Um atendente pergunta: *"Qual o limite de peso por volume para carga não consolidada conforme a norma NS-047?"*. O OCR leu `"peso máximo: 1.500 kg"` corretamente na primeira ocorrência, mas em outra página do mesmo documento leu `"peso máximo: l.5OO kg"` (L minúsculo no lugar do 1, O maiúsculo no lugar do zero). O retriever recupera ambos os chunks. O GPT-4o interpreta o segundo como texto corrompido, ignora o valor e responde com base apenas no primeiro — que pode ser de uma versão anterior do documento, com limite diferente. O atendente passa a informação errada e, se ocorrer um sinistro de carga, a NovaTech pode ter responsabilidade contratual comprometida.

Há ainda o problema de documentos escaneados com baixa resolução (abaixo de 150 DPI) onde o OCR retorna blocos de texto completamente ininteligíveis que são indexados normalmente. Esses chunks "fantasma" aparecem nos resultados do retriever por similaridade semântica superficial, contaminam o contexto do GPT-4o e aumentam a probabilidade de alucinação.

### Estratégias de tratamento

**Estratégia A — OCR com Azure Document Intelligence + camada de validação pós-extração** ⭐ *Estratégia mais indicada*

Utilizar o modelo `prebuilt-read` do Azure Document Intelligence, que opera com modelos treinados para documentos de negócios e retorna confidence scores por palavra. Implementar um filtro de qualidade: chunks com confidence médio abaixo de 0,80 são sinalizados para revisão humana antes de serem indexados. Adicionalmente, criar um dicionário de termos logísticos específicos da NovaTech para pós-processamento OCR (normalização de abreviações conhecidas, correção de padrões numéricos).

**Impacto no chunking:** sim, exige uma etapa de pré-chunking para descartar ou isolar trechos de baixa confiança. Chunks com score misto (parte confiável, parte corrompida) devem ser truncados no ponto de queda de confiança, não pelo limite de tokens. Isso garante que apenas texto com integridade verificada entre no índice vetorial.

**Estratégia B — Re-digitalização e OCR com pré-processamento de imagem**

Aplicar pré-processamento (deskew, binarização adaptativa, remoção de ruído) com ferramentas como OpenCV antes do OCR com Tesseract 5 ou Google Vision. Útil para documentos com distorção geométrica severa.

**Impacto no chunking:** não altera diretamente a estratégia de chunking, mas melhora a matéria-prima. A limitação é o custo operacional: reprocessar 800 documentos com pipeline de visão computacional exige infraestrutura e tempo, e documentos com qualidade irrecuperável (abaixo de 100 DPI, manchas, dobras) continuarão problemáticos mesmo após o pré-processamento.

---

## 3. Wiki do Confluence (Links Internos + Macros Customizadas)

### Desafio específico para o pipeline de RAG

O Confluence é construído sobre uma estrutura de grafo: páginas referenciam outras páginas, seções são definidas por macros (`{include}`, `{excerpt}`, `{children}`), e o conteúdo real pode estar distribuído entre página-pai, páginas-filhas e páginas incluídas dinamicamente. Quando a exportação é feita via API REST do Confluence (formato storage XML ou HTML), o conteúdo das macros `{include}` e `{excerpt-include}` não é resolvido — a exportação retorna a tag da macro, não o conteúdo que ela injeta na renderização.

No contexto da NovaTech, isso significa que uma página de procedimento operacional pode conter `{include: Política de Devolução Vigente}` — e o texto exportado para o pipeline RAG simplesmente não terá o conteúdo dessa política. O chunk indexado estará semanticamente incompleto sem que nenhum erro seja gerado.

Links internos (`[Clique aqui para ver a tabela de SLA|NovaTech:SLA_Clientes]`) são exportados como texto literal do anchor, perdendo completamente a informação de destino. O atendente que pergunta sobre SLA recebe uma resposta que menciona "conforme a tabela de SLA" sem que o pipeline tenha indexado o conteúdo dessa tabela se ela estava em outra página não recuperada.

### Como isso afeta a qualidade das respostas

Um atendente pergunta: *"Qual o procedimento correto para registrar uma reclamação de carga avariada?"*. A página do Confluence sobre reclamações tem a estrutura do processo, mas delega os prazos para uma página-filha via macro `{children}` e os formulários via `{include}`. O chunk recuperado descreve o fluxo geral, mas quando o GPT-4o tenta responder sobre "em quantos dias o cliente deve notificar", a informação simplesmente não está no contexto — porque estava na página-filha não recuperada. O modelo então ou alucina um prazo plausível ou responde de forma evasiva, obrigando o atendente a continuar a busca manual — exatamente o comportamento que a solução deveria eliminar.

### Estratégias de tratamento

**Estratégia A — Exportação via API com resolução de grafo de dependências** ⭐ *Estratégia mais indicada*

Usar a API REST do Confluence para construir um mapa de dependências entre páginas antes da exportação: identificar todas as relações `{include}`, `{excerpt-include}` e links internos, e resolver o grafo recursivamente para garantir que todas as páginas referenciadas sejam exportadas e indexadas. Durante o chunking, enriquecer cada chunk com metadados de contexto hierárquico (`space_key`, `parent_page_title`, `linked_pages[]`), permitindo que o retriever recupere chunks relacionados via filtragem de metadados além da similaridade semântica.

**Impacto no chunking:** sim, altera a estratégia. Páginas que funcionam como "hubs" (muito referenciadas) devem ser chunked de forma a preservar sua identidade como referência centralizada. Páginas-filha devem carregar o contexto da página-pai nos metadados de cada chunk, evitando que um chunk filho seja recuperado sem que o modelo entenda a que procedimento ele pertence.

**Estratégia B — Exportação por renderização de página (HTML scraping)**

Acessar cada página via URL pública do Confluence e capturar o HTML renderizado pelo navegador (via Playwright ou Selenium), que resolve todas as macros no cliente. O conteúdo capturado é o que o usuário veria na tela, macros incluídas.

**Impacto no chunking:** não altera a estratégia de chunking em si, mas garante que o conteúdo seja completo antes de chunkar. A limitação é o custo de manutenção: a cada atualização mensal, o crawler precisa ser reexecutado para todas as 400 páginas, e mudanças na estrutura de autenticação do Confluence podem quebrar o processo silenciosamente.

---

## 4. Planilhas com Fórmulas Interdependentes

### Desafio específico para o pipeline de RAG

Planilhas de referência logística (tabelas de custo por km, coeficientes de sazonalidade, multiplicadores por tipo de carga especial) armazenam conhecimento de duas formas: nos valores calculados das células e na lógica das fórmulas. Um pipeline RAG padrão extrai apenas os valores estáticos no momento da exportação — ignora completamente as fórmulas.

O problema crítico é que planilhas atualizadas mensalmente funcionam com valores de entrada que mudam (índice de combustível, taxa cambial para cargas internacionais, tabela ANTT atualizada) e fórmulas que calculam os valores derivados. Se a exportação captura os valores calculados de uma planilha de janeiro e em fevereiro os inputs mudam, o índice vetorial passa a conter valores desatualizados sem nenhum aviso. Além disso, fórmulas como `=PROCV(peso, TabelaFaixas, 4, VERDADEIRO)` implementam lógica de negócio — definem qual faixa de preço se aplica a qual peso — e essa lógica de faixa é completamente invisível para o pipeline se apenas os resultados são exportados.

### Como isso afeta a qualidade das respostas

Um atendente pergunta: *"Qual o valor do seguro obrigatório para uma carga de R$ 80.000 transportada para a região Sul?"*. A planilha tem uma fórmula que aplica 0,3% para NF até R$100.000 e 0,25% para NF acima desse valor. O pipeline indexou os valores calculados de dezembro, quando o input era R$75.000. Em janeiro, o mesmo tipo de carga passou a custar R$82.000 — mas o chunk ainda diz R$225,00 (calculado sobre o valor antigo). O atendente informa R$225,00, o cliente é cobrado R$246,00 (valor correto recalculado pelo sistema de faturamento), e a discrepância gera contestação. A fonte de erro é rastreada até o assistente de IA, corroendo a confiança da equipe na ferramenta.

Fórmulas com referências entre abas (`=Aba_Sazonalidade!B12 * Aba_Frete!C8`) criam dependências que, quando a planilha é exportada aba por aba, resultam em células com `#REF!` ou `0` onde deveria haver um valor calculado — e esse zero é indexado como dado válido.

### Estratégias de tratamento

**Estratégia A — Não indexar planilhas diretamente; convertê-las em documentos de regras versionados** ⭐ *Estratégia mais indicada*

Implementar um processo de curadoria onde as planilhas não alimentam o pipeline RAG diretamente. Em vez disso, a cada atualização mensal, um processo automatizado (Azure Logic Apps ou Power Automate) exporta os valores calculados e os transforma em documentos de regras em linguagem natural: `"Para cargas com NF entre R$50.000 e R$100.000 transportadas para a Região Sul, o seguro obrigatório é de 0,3% sobre o valor declarado (vigência: fevereiro/2025)"`. Esses documentos substituem a versão anterior no índice com versionamento explícito.

**Impacto no chunking:** sim, altera completamente a estratégia. O chunk não é derivado da planilha bruta, mas do documento de regras gerado. Cada regra de negócio vira um chunk autônomo com metadado de `data_vigência`, permitindo que o retriever filtre por versão atual e que o GPT-4o receba contexto com data de validade explícita, o que ele pode incluir na resposta para o atendente.

**Estratégia B — Exportação com OpenPyXL capturando valores calculados + metadado de data**

Usar OpenPyXL com `data_only=True` para capturar os valores calculados no momento da última edição da planilha, acompanhados de metadado de data de extração. Implementar alertas de desatualização: se a data de modificação da planilha for mais recente que a data de indexação, o chunk é marcado como potencialmente desatualizado nas respostas.

**Impacto no chunking:** não altera a estratégia de chunking em si, mas adiciona uma camada de metadados temporais. A limitação é que fórmulas com `#REF!` ou dependências entre abas continuam gerando valores incorretos (zero ou erro), e o pipeline não tem como distinguir automaticamente um zero legítimo de um zero oriundo de referência quebrada.

---

## Conclusão: Maior Risco para a Qualidade do Pipeline

**As planilhas com fórmulas interdependentes representam o maior risco sistêmico** para a qualidade do pipeline RAG da NovaTech — e a razão não é técnica, é temporal. Todos os outros tipos de fonte têm problemas de extração que ocorrem no momento da ingestão e podem ser detectados e corrigidos antes do deploy. As planilhas, por outro lado, introduzem um vetor de degradação contínua: são atualizadas mensalmente por três áreas diferentes, sem processo unificado, e qualquer defasagem entre a atualização da planilha e a reindexação do pipeline produz respostas factualmente incorretas sobre valores monetários e prazos — os dois tipos de informação com maior impacto direto em disputas comerciais e SLA. Diferentemente de um chunk com OCR ruim (que o atendente provavelmente perceberá como corrompido) ou de um link quebrado do Confluence (que gera uma resposta incompleta, não errada), uma planilha desatualizada indexada corretamente produz respostas confiantes e precisas sobre dados que já não são mais verdadeiros — o pior tipo de erro possível em um sistema de suporte ao cliente.