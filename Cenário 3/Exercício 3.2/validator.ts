import { z } from "zod";

export const feedbackRequestSchema = z.object({
	queryId: z.string().uuid(),
	rating: z.number().int().min(1).max(5),
	comment: z.string().trim().max(1000).optional(),
	attendantEmail: z.string().trim().email()
}).strict();

export type FeedbackRequest = z.infer<typeof feedbackRequestSchema>;

export type FeedbackRecord = FeedbackRequest & {
	timestamp: string;
};
