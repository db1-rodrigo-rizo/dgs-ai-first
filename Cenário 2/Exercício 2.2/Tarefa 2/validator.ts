import { z } from "zod";

export const queryRequestSchema = z.object({
	question: z.string().trim().min(1).max(2000)
});

export type QueryRequest = z.infer<typeof queryRequestSchema>;
