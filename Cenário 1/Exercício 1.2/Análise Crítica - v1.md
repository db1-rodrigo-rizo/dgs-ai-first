# Bateria de testes realizados

Pergunta 1: Qual o prazo de devolução para carga perigosa?
- Chunk utilizado: Chunk A: "Política de Devolução POL-001, seção 3.2: Mercadorias podem ser devolvidas em até 7 dias úteis após o recebimento, exceto cargas classificadas como perigosas (classes 1 a 6 da ANTT). O cliente deve abrir chamado no portal e anexar fotos da mercadoria."
- Resposta obtida:
  - RESPOSTA DIRETA: A documentação não define um prazo de devolução específico para cargas perigosas. Essa categoria está explicitamente excluída da política geral de 7 dias úteis.
  - FONTE: [Fonte: Política de Devolução POL-001 · seção 3.2]
  - ATENÇÃO: Não encontrei na documentação disponível uma regra alternativa para devolução de cargas perigosas. Recomendo escalar para o supervisor ou consultar a equipe responsável pela área antes de responder ao cliente.

Pergunta 2: Meu cliente é Gold, qual o SLA de resolução?
- Chunk utilizado: Chunk B: "Tabela SLA-2024: Cliente Gold — resposta em até 2h, resolução em até 24h. Cliente Silver — resposta em até 4h, resolução em até 48h. Cliente Standard — resposta em até 8h, resolução em até 72h."
- Resposta obtida:
  - RESPOSTA DIRETA: Para clientes Gold, o prazo de resolução é de até 24 horas.
  - DETALHES:
    - Tempo de resposta inicial: até 2h
    - Tempo de resolução: até 24h
  - FONTE: [Fonte: Tabela SLA-2024 · sem seção especificada]

Pergunta 3: Quanto custa o frete para 600kg para Manaus?
- Chunk utilizado: Chunk C: "PROC-042-v2, seção 2: Frete especial para cargas acima de 500kg: valor base × multiplicador regional. Região Sul: 1.3. Região Sudeste: 1.1. Região Norte: 1.8. Região Nordeste: 1.5. Região Centro-Oeste: 1.4."
- Resposta obtida:
  - RESPOSTA DIRETA: Não é possível calcular o valor final. O documento fornece apenas o multiplicador regional (1.8 para a Região Norte), mas não indica o valor base a ser utilizado no cálculo.
                     A fórmula é: valor base × 1.8 — porém o valor base não consta nos trechos disponíveis para esta consulta.
  - FONTE: [Fonte: PROC-042-v2 · seção 2]
  - ATENÇÃO: Recomendo consultar o documento completo ou escalar para o supervisor para obter o valor base e concluir o cálculo.

# Análise qualitativa das respostas obtidas

| Critério                           | Pergunta 1 | Pergunta 2 | Pergunta 3 |
|------------------------------------|------------|------------|------------|
|Informação tecnicamente correta?    |     Sim    |     Sim    |     Sim    |
|Respeitou os guardrails             |     Sim    |     Sim    |     Sim    |
|Citou documento e seção?            |     Sim    |Parcialmente|     Sim    |
|Inventou valor ou prazo?            |     Não    |     Não    |     Não    |
|Admitiu quando não tinha informação?|     Sim    |     ---    |     Sim    |
|Linguagem formal e acessível?       |     Sim    |     Sim    |     Sim    |

O System Prompt v1 teve um desempenho satisfatório, pois deu respostas tecnicamente corretas para todas as perguntas e respeitou os guardrails. Porém, existem algumas ressalvas:

  - A resposta para a pergunta 1 foi relativamente imprecisa, pois ele afirma que não existe um prazo definido para cargas perigosas, mas poderia ser mais assertivo ao afirmar que "devoluções NÃO são permitidas para a categoria".
  - A resposta para a pergunta 2, apesar de correta e detalhada, informa que não encontrou sessão especificada na fonte.
