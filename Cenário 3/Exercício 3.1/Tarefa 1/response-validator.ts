import { z } from "zod";

export const assistantResponseSchema = z.object({
	answer: z.string().trim().min(1),
	source_document: z.string().trim().min(1),
	confidence_score: z.number().min(0).max(1)
}).strict();

export type AssistantResponse = z.infer<typeof assistantResponseSchema>;
