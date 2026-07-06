import { z } from "zod";
import pino from "pino";

export const assistantResponseSchema = z.object({
	answer: z.string().trim().min(1),
	source_document: z.string().trim().min(1),
	confidence_score: z.number().min(0).max(1)
}).strict();

export type AssistantResponse = z.infer<typeof assistantResponseSchema>;

export type ValidatedResponse = AssistantResponse & {
	blocked: boolean;
};

const logger = pino({ name: "response-validator" });

const safeDefaultResponse: ValidatedResponse = {
	answer: "Não foi possível processar esta resposta. Por favor, consulte um supervisor.",
	source_document: "",
	confidence_score: 0,
	blocked: true
};

function normalizeForGuardrail(text: string): string {
	return text
		.normalize("NFD")
		.replace(/[\u0300-\u036f]/g, "")
		.toLowerCase();
}

export function validateResponse(raw: unknown): ValidatedResponse {
	const parsed = assistantResponseSchema.safeParse(raw);

	if (!parsed.success) {
		logger.warn(
			{
				issues: parsed.error.issues
			},
			"assistant response schema validation failed"
		);

		return { ...safeDefaultResponse };
	}

	const validated = parsed.data;

	if (validated.source_document.trim().length === 0) {
		logger.warn(
			{
				source_document: validated.source_document
			},
			"guardrail blocked response: source_document is empty"
		);

		return { ...safeDefaultResponse };
	}

	const normalizedAnswer = normalizeForGuardrail(validated.answer);
	const hasDangerousCargoReference = /(\bcarga perigosa\b|\bcargas perigosas\b)/i.test(normalizedAnswer);
	const hasReturnReference = /(\bdevolucao\b|\bdevolver\b|\bdevolvida\b|\bdevolva\b)/i.test(normalizedAnswer);
	const hasExplicitNegative = /(\bnao\b|\bimpossivel\b|\bvedado\b|\bproibido\b)/i.test(normalizedAnswer);

	if (hasDangerousCargoReference && hasReturnReference && !hasExplicitNegative) {
		logger.warn(
			{
				answer: validated.answer,
				reason: "dangerous cargo return guidance without explicit prohibition"
			},
			"guardrail blocked response: potentially unsafe return guidance"
		);

		return { ...safeDefaultResponse };
	}

	return {
		...validated,
		blocked: false
	};
}
