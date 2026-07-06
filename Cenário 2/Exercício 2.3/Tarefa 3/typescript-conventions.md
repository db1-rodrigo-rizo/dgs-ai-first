# TypeScript Conventions

## Contexto

Use esta skill sempre que um agente for gerar ou editar um arquivo `.ts` ou `.tsx` neste repositório.

Ela define a base obrigatória para escrita de TypeScript no projeto. Skills de Domain e Artifact devem assumir estas convenções como padrão antes de introduzir regras específicas de framework, endpoint, UI ou integração.

## Regras Prescritivas

### 1. Respeite `strict: true`

O `tsconfig.json` do projeto já usa `strict: true`. Isso não é opcional.

- Não contorne erros de tipo com casts desnecessários.
- Casts amplos como `as any` ou `as unknown as SomeType` são proibidos por padrão.
- A única exceção aceitável é interoperabilidade com biblioteca externa ou API sem tipos adequados, e mesmo assim o cast deve vir acompanhado de um comentário curto explicando por que a conversão é segura.
- Não enfraqueça contratos para “fazer compilar”.
- Modele estados intermediários de forma explícita quando o valor ainda não foi validado.

### 2. Declare retorno explícito em funções exportadas ou públicas

Funções exportadas, handlers, factories públicas e utilitários compartilhados devem declarar o tipo de retorno explicitamente.

- Prefira `Promise<HttpResponseInit>` a depender de inferência implícita em handlers.
- Prefira declarar o tipo mesmo quando a inferência “funciona”, porque isso estabiliza o contrato público do módulo.

### 3. Nunca use `any`

`any` é proibido neste repositório.

- Quando o tipo ainda não é conhecido, use `unknown`.
- Faça narrowing explícito ou valide o valor antes de usá-lo.
- Exemplo típico: body de requisição HTTP antes da validação Zod.

### 4. Organize imports por origem

A ordem padrão é:

1. Bibliotecas externas.
2. Imports internos do projeto.

Regras adicionais:

- Separe os grupos com uma linha em branco.
- Não misture `require` com `import`.
- Mantenha o estilo de módulos consistente com o arquivo e com o projeto.

### 5. Siga a nomenclatura padrão

- `camelCase` para variáveis, funções, parâmetros e instâncias.
- `PascalCase` para tipos, interfaces, classes e aliases de tipo exportados.

Exemplos esperados:

- `queryHandler`
- `queryRequestSchema`
- `QueryRequest`
- `withCors`
- `corsHeaders`

## Exemplos Concretos: DO / DON'T

Os exemplos abaixo usam como referência o endpoint de query em `src/functions/query/handler.ts` e `src/functions/query/validator.ts`.

### DO: tipar explicitamente um handler exportado

```ts
import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import pino from "pino";

import { queryRequestSchema } from "./validator.js";

export async function queryHandler(
	request: HttpRequest,
	_context: InvocationContext
): Promise<HttpResponseInit> {
	// ...
}
```

Por que está correto:

- O contrato público da função fica explícito.
- `HttpRequest`, `InvocationContext` e `HttpResponseInit` deixam claro o papel do handler.
- Imports externos aparecem antes do import interno.

### DON'T: deixar função exportada com retorno implícito

```ts
export async function queryHandler(request: HttpRequest, context: InvocationContext) {
	return { received: true };
}
```

Problema:

- O retorno público fica dependente de inferência.
- O contrato pode mudar sem sinal claro ao editar o corpo da função.

### DO: usar `unknown` antes da validação

```ts
let body: unknown;

try {
	body = await request.json();
} catch (error) {
	logger.warn({ method: request.method, path: request.url, error }, "malformed JSON body");
	return withCors({
		status: 400,
		jsonBody: { error: "Malformed JSON body" }
	});
}

const result = queryRequestSchema.safeParse(body);
```

Por que está correto:

- O body ainda não é confiável antes do parse e da validação.
- `unknown` força validação ou narrowing antes do uso.

### DON'T: usar `any` no body para “resolver rápido”

```ts
const body: any = await request.json();
const question = body.question.trim();
```

Problema:

- Remove proteção do `strict`.
- Permite acesso inseguro a propriedades antes da validação.
- Mascara erros que o Zod deveria capturar.

### DO: centralizar schema Zod em validator dedicado

```ts
import { z } from "zod";

export const queryRequestSchema = z.object({
	question: z.string().trim().min(1).max(2000)
});

export type QueryRequest = z.infer<typeof queryRequestSchema>;
```

Por que está correto:

- O schema fica separado do handler.
- O tipo derivado do schema evita divergência entre validação e tipagem.
- `QueryRequest` segue `PascalCase`.

### DON'T: misturar validação inline e tipos soltos

```ts
type queryRequest = {
	question: string;
};

export async function queryHandler(request: HttpRequest): Promise<HttpResponseInit> {
	const body: unknown = await request.json();
	const payload = body as queryRequest;

	if (!payload.question || payload.question.trim().length === 0) {
		return { status: 400 };
	}

	return { status: 200 };
}
```

Problema:

- `queryRequest` viola a convenção de `PascalCase` para tipos.
- A validação manual é frágil e diverge do padrão Zod do projeto.
- O cast para um tipo local não substitui validação estrutural real do payload.

### DO: manter imports organizados por grupo

```ts
import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import pino from "pino";

import { queryRequestSchema } from "./validator.js";
```

### DON'T: misturar ordem de imports ou sintaxes diferentes

```ts
const pino = require("pino");
import { queryRequestSchema } from "./validator.js";
import { HttpRequest } from "@azure/functions";
```

Problema:

- Mistura CommonJS com ESM sem necessidade.
- Quebra consistência visual e semântica do módulo.
- Dificulta manutenção automática por formatter e tooling.

## Anti-padrões

Erros comuns que agentes de IA cometem ao gerar TypeScript sem esta guidance:

1. Usar `any` para eliminar erro de tipo rapidamente em vez de modelar o estado como `unknown` e validar.
2. Omitir o tipo de retorno de funções exportadas, especialmente handlers e utilitários compartilhados.
3. Acessar propriedades de `request.json()` antes de validação ou narrowing.
4. Declarar tipos com nomenclatura inconsistente, como `queryRequest` em vez de `QueryRequest`.
5. Misturar `require` e `import` no mesmo arquivo.
6. Misturar imports externos e internos sem agrupamento claro.
7. Duplicar contratos manualmente em vez de derivar tipos a partir do schema Zod com `z.infer`.
8. Resolver erro de `strict` com cast amplo, como `as any` ou `as unknown as SomeType`; esse tipo de cast é proibido por padrão e só pode existir em exceção documentada com comentário explicando por que é seguro.

## Regra Operacional

Antes de concluir qualquer geração ou edição de arquivo TypeScript neste repositório, o agente deve verificar se:

1. Nenhum `any` foi introduzido.
2. Toda função exportada relevante tem retorno explícito.
3. Valores externos não validados começaram como `unknown`.
4. Imports externos e internos estão em grupos separados.
5. Nomes seguem `camelCase` e `PascalCase` conforme a categoria.
