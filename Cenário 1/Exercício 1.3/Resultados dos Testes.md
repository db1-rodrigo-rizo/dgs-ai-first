# Resultados dos Testes — Pipeline de RAG NovaTech

## Metodologia

Cada teste consiste em enviar uma pergunta ao script `busca.py`, observar os 5 chunks retornados com seus respectivos scores de similaridade, e comparar o resultado com o gabarito definido no Anexo B. A avaliação considera três critérios:

- **Chunks corretos recuperados:** se os chunks esperados pelo gabarito estão entre os 5 retornados
- **Posição no ranking:** se os chunks corretos estão no topo ou no final da lista
- **Chunks irrelevantes:** se chunks sem relação com a pergunta ocupam posições altas

---

## Teste 1 — Prazo de devolução

**Pergunta enviada:** "Qual é o prazo para devolução?"  
*(Testada também como "Qual o prazo de devolução?" — mesma resposta obtida nas duas formulações)*

**Chunks esperados pelo gabarito (Anexo B):**
- `POL-001-A` — Seção 3.1: prazo geral de 7 dias úteis *(principal)*
- `POL-001-B` — Seção 3.2: exceções ao prazo *(principal)*
- `POL-001-C` — Seção 3.3: procedimento *(secundário)*

**Chunks retornados pelo pipeline:**

| Pos. | Score | Arquivo | Seção | Avaliação |
|------|-------|---------|-------|-----------|
| 1 | 0.5656 | POL-001-politica-devolucao.md | 3.5. Custos de devolução | ❌ Incorreto |
| 2 | 0.5460 | PROC-042-frete-especial-v1.md | 3. Prazo de entrega para frete especial | ❌ Incorreto |
| 3 | 0.5361 | FAQ-atendimento.md | Item 3 — Carga perigosa | ⚠️ Parcialmente relevante |
| 4 | 0.5248 | PROC-042-frete-especial-v1.md | 4. Condições especiais | ❌ Incorreto |
| 5 | 0.5202 | FAQ-atendimento.md | Item 45 — Desconto no frete | ❌ Irrelevante |

**Resultado:** ❌ Falha — nenhum dos chunks esperados foi recuperado. O chunk mais importante (POL-001 seção 3.1, com o prazo de 7 dias úteis) não apareceu entre os 5 retornados.

---

## Teste 2 — Devolução de carga perigosa

**Pergunta enviada:** "Posso devolver carga perigosa?"

**Chunks esperados pelo gabarito (Anexo B):**
- `POL-001-B` — Seção 3.2: exceções (carga perigosa NÃO é elegível) *(principal)*
- `FAQ-03` — Item 3: orientação informal sobre carga perigosa *(secundário)*

**Chunks retornados pelo pipeline:**

| Pos. | Score | Arquivo | Seção | Avaliação |
|------|-------|---------|-------|-----------|
| 1 | 0.5154 | PROC-042-frete-especial-v1.md | 4. Condições especiais | ❌ Incorreto |
| 2 | 0.5123 | FAQ-atendimento.md | Item 22 — Seguro de carga | ❌ Irrelevante |
| 3 | 0.4990 | POL-001-politica-devolucao.md | 2. Escopo | ❌ Incorreto |
| 4 | 0.4984 | FAQ-atendimento.md | Item 27 — Tracking | ❌ Irrelevante |
| 5 | 0.4935 | FAQ-atendimento.md | Item 3 — Carga perigosa | ⚠️ Correto como secundário |

**Resultado:** ❌ Falha crítica — o chunk principal (`POL-001-B`, que contém a regra de exclusão de cargas perigosas) não foi recuperado. O único chunk relevante chegou em último lugar. Um LLM operando com este contexto correria risco de responder que a devolução é possível com base no FAQ informal, invertendo a regra da política oficial.

---

## Teste 3 — SLA do cliente Gold

**Pergunta enviada:** "Qual o SLA do cliente Gold?"

**Chunks esperados pelo gabarito (Anexo B):**
- `SLA-2024-B` — Seção 2: tabela de SLAs com tempos de resposta e resolução *(principal)*
- `SLA-2024-A` — Seção 1: classificação de clientes *(secundário)*

**Chunks retornados pelo pipeline:**

| Pos. | Score | Arquivo | Seção | Avaliação |
|------|-------|---------|-------|-----------|
| 1 | 0.5713 | SLA-2024-tabela-sla-clientes.md | 5. Medição e reportes | ❌ Incorreto |
| 2 | 0.5443 | SLA-2024-tabela-sla-clientes.md | 1. Classificação de clientes | ✅ Correto como secundário |
| 3 | 0.5386 | FAQ-atendimento.md | Item 15 — Tier Platinum | ❌ Irrelevante |
| 4 | 0.5374 | SLA-2024-tabela-sla-clientes.md | 2. Tabela de SLAs | ⚠️ Seção correta, mas fragmentada (linha: gerente de conta) |
| 5 | 0.5247 | SLA-2024-tabela-sla-clientes.md | 2. Tabela de SLAs | ⚠️ Seção correta, mas fragmentada (linha: relatório mensal) |

**Resultado:** ❌ Falha — a seção correta (2. Tabela de SLAs) apareceu duas vezes, mas em posições baixas e fragmentada em linhas individuais. Os tempos de resposta e resolução do cliente Gold não foram retornados. A tabela foi dividida em um chunk por linha durante a ingestão, destruindo o contexto estrutural.

---

## Teste 4 — Frete para 600kg para Manaus

**Pergunta enviada:** "Frete para 600kg para Manaus?"

**Chunks esperados pelo gabarito (Anexo B):**
- `PROC-042v2-B` — Seção 2.1: multiplicadores regionais atualizados (Norte: 1.8) *(principal)*
- `PROC-042v2-A` — Seção 2: fórmula atualizada *(principal)*
- `PROC-042-B` — Seção 2.1 v1: multiplicadores antigos *(risco de contradição)*

**Chunks retornados pelo pipeline:**

| Pos. | Score | Arquivo | Seção | Avaliação |
|------|-------|---------|-------|-----------|
| 1 | 0.5066 | FAQ-atendimento.md | Item 27 — Tracking | ❌ Irrelevante |
| 2 | 0.4857 | PROC-042-frete-especial-v1.md | 2. Fórmula de cálculo | ⚠️ Versão desatualizada |
| 3 | 0.4848 | PROC-042-v2-frete-especial-revisado.md | 1. Objetivo | ❌ Irrelevante |
| 4 | 0.4819 | PROC-042-frete-especial-v1.md | 4. Condições especiais | ❌ Incorreto |
| 5 | 0.4754 | PROC-042-v2-frete-especial-revisado.md | 2. Fórmula de cálculo | ⚠️ Correto, mas em último lugar |

**Resultado:** ❌ Falha — os chunks com os multiplicadores regionais (a resposta direta para "Manaus = região Norte") não foram recuperados. A fórmula da versão desatualizada (v1) ranqueou acima da versão atual (v2). Chunks das duas versões do PROC-042 apareceram juntos, com fatores de peso contraditórios (1.2 vs 1.15 para a faixa de 1.001–3.000kg).

---

## Teste 5 — Multiplicador para o Sudeste

**Pergunta enviada:** "Qual o multiplicador para o Sudeste?"

**Chunks esperados pelo gabarito (Anexo B):**
- `PROC-042v2-B` — Seção 2.1: multiplicador Sudeste atualizado (1.1) *(principal)*
- `PROC-042-B` — Seção 2.1 v1: multiplicador Sudeste antigo (1.0) *(risco de contradição)*

**Chunks retornados pelo pipeline:**

| Pos. | Score | Arquivo | Seção | Avaliação |
|------|-------|---------|-------|-----------|
| 1 | 0.5921 | PROC-042-frete-especial-v1.md | 2.1. Multiplicadores regionais | ⚠️ Correto, mas versão desatualizada |
| 2 | 0.5833 | PROC-042-v2-frete-especial-revisado.md | 2.1. Multiplicadores regionais (nov/2023) | ✅ Correto e atualizado |
| 3 | 0.5353 | PROC-042-frete-especial-v1.md | 2.1. Multiplicadores regionais | ❌ Outra região (Centro-Oeste v1) |
| 4 | 0.5324 | PROC-042-frete-especial-v1.md | 2.1. Multiplicadores regionais | ❌ Outra região (Sul v1) |
| 5 | 0.5220 | PROC-042-v2-frete-especial-revisado.md | 2.1. Multiplicadores regionais (nov/2023) | ❌ Outra região (Centro-Oeste v2) |

**Resultado:** ⚠️ Parcial — o teste 5 é o único em que os chunks mais relevantes foram recuperados. Porém, a versão desatualizada (v1, multiplicador 1.0) ranqueou acima da versão atual (v2, multiplicador 1.1). Um LLM recebendo ambos os valores sem instrução de prioridade de versão produziria uma resposta contraditória ou incorreta.

---

## Resumo consolidado

| Teste | Pergunta | Chunks corretos recuperados | Resultado |
|-------|----------|-----------------------------|-----------|
| 1 | Prazo de devolução | 0 de 2 esperados | ❌ Falha |
| 2 | Devolução de carga perigosa | 1 de 2 esperados (em último lugar) | ❌ Falha crítica |
| 3 | SLA do cliente Gold | 1 de 2 esperados (fragmentado) | ❌ Falha |
| 4 | Frete 600kg para Manaus | 1 de 2 esperados (em último lugar) | ❌ Falha |
| 5 | Multiplicador para o Sudeste | 2 de 2 esperados (versão errada em 1º) | ⚠️ Parcial |

Os resultados evidenciam que o pipeline funciona tecnicamente — ingere documentos, gera embeddings e realiza busca por similaridade — mas apresenta problemas sistemáticos de qualidade de retrieval que comprometem a confiabilidade das respostas. As causas e propostas de correção estão detalhadas no documento **Análise de Problemas e Propostas de Correção**.
