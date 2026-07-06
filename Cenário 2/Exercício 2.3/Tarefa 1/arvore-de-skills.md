# Árvore de Skills do Projeto

> Hierarquia Foundation → Domain → Artifact, seguindo a estrutura de diretórios do Anexo C (`/skills/foundation/`, `/skills/domain/`, `/skills/artifact/`).

```
skills/
├── foundation/
│   ├── typescript-conventions.md
│   ├── error-handling.md
│   ├── project-structure.md
│   ├── logging-standards.md
│   └── env-config.md
│
├── domain/
│   ├── azure-functions-endpoint.md
│   ├── testing-patterns.md
│   ├── react-components.md
│   ├── technical-documentation.md
│   └── spec-sdd-template.md
│
└── artifact/
    ├── create-rag-endpoint.md
    ├── create-integration-test.md
    ├── create-react-card.md
    ├── create-adr.md
    └── create-product-spec.md
```

---

## Racional da hierarquia

**Foundation** — convenções que se aplicam a *qualquer* código ou artefato gerado no repositório, independentemente da camada ou do módulo. São a base sobre a qual as skills de Domain se apoiam.

**Domain** — um padrão por camada/tipo de trabalho recorrente no projeto. Cada skill de Domain corresponde a um dos 5 artefatos produzidos repetidamente ao longo do projeto (endpoints, testes, componentes React, documentação técnica, specs de produto).

**Artifact** — receitas de geração concretas, uma por artefato recorrente, cada uma dependente de sua skill de Domain correspondente (ex: `create-rag-endpoint` depende de `azure-functions-endpoint`).

---

## Cobertura dos 5 artefatos recorrentes do enunciado

| Artefato recorrente | Skill de Domain | Skill de Artifact |
|---|---|---|
| Endpoints Azure Functions com padrão RAG | `azure-functions-endpoint` | `create-rag-endpoint` |
| Testes de integração para endpoints | `testing-patterns` | `create-integration-test` |
| Componentes React para o painel web | `react-components` | `create-react-card` |
| Documentação técnica de endpoints | `technical-documentation` | `create-adr` |
| Specs de produto (SDD) | `spec-sdd-template` | `create-product-spec` |
