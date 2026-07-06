# Exercício 2.1 — Tarefa 2: Justificativa de Least Privilege do `.mcp/mcp.json`

---

## 1. `filesystem-code-read-write`

**Pastas:** `./src`, `./specs`, `./skills`
**Acesso:** leitura e escrita

As três pastas estão na mesma instância porque uma única tarefa de desenvolvimento pode passar pelas três ao mesmo tempo.

Implementar uma task envolve:
  - ler o plan.md/tasks.md em ./specs;
  - escrever o código correspondente em ./src;
  - consultar skills em ./skills para seguir o padrão do projeto, por exemplo.
  
Separar essas três pastas em instâncias diferentes não reduziria risco real (todas já são de trabalho do dev, não fontes de negócio) e só adicionaria complexidade operacional sem ganho de segurança.

---

## 2. `filesystem-docs-readonly`

**Pastas:** `./docs/novatech`, `./data/retrieval-corpus`
**Acesso:** somente leitura

Estas pastas ficam separadas da instância de código porque são fontes de verdade de negócio (documentação da NovaTech) e dados curados de teste (corpus de chunks), não artefatos de engenharia. Misturá-las na mesma instância de ./src daria ao agente a mesma permissão de escrita nelas — expondo a documentação e os dados de teste a alguma alteração acidental durante uma tarefa de codificação.

**Ressalva:** o modo npx não trava escrita por pasta de fato. A separação em instância própria não é uma garantia técnica absoluta — é uma segregação lógica que reduz a probabilidade de escrita acidental (o agente não tem motivo nem instrução para escrever ali) mas não a impede tecnicamente. A garantia real de que o agente não vai escrever nessas pastas depende de uma regra explícita no AGENTS.md (ex: "nunca edite arquivos em docs/novatech/ ou data/retrieval-corpus/"), que atua como controle de processo complementar ao controle técnico insuficiente do server.

---

## 3. `git`

**Escopo:** repositório local (`.`)
**Acesso:** leitura e escrita (commit/branch sujeitos a autorização do dev)

O escopo é o repositório inteiro porque o mcp-server-git opera no nível do repositório. Histórico, diffs e branches não são "por pasta", são propriedades do repositório como um todo. Restringir o `--repository` a uma subpasta quebraria a funcionalidade (o Git precisa do .git na raiz para funcionar).

---

## 4. `memory`

**Escopo:** grafo local interno ao server
**Acesso:** leitura e escrita

Esse escopo é o mínimo possível porque o memory server não expõe pastas do sistema de arquivos. Ele mantém um grafo de entidades e relações interno, isolado do resto do repositório. Não há como restringir "mais" sem impedir sua função central, que é justamente persistir e recuperar informação (linguagem ubíqua, decisões) entre sessões.