import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import { CosmosClient, Container } from "@azure/cosmos";
import pino from "pino";

import { feedbackRequestSchema, FeedbackRecord } from "./validator.js";

const logger = pino({ name: "feedback-endpoint" });
const corsHeaders = {
	"Access-Control-Allow-Origin": "*",
	"Access-Control-Allow-Methods": "POST, OPTIONS",
	"Access-Control-Allow-Headers": "Content-Type"
};

const cosmosConnectionString = process.env.COSMOS_CONNECTION_STRING;

if (!cosmosConnectionString) {
	throw new Error("COSMOS_CONNECTION_STRING não configurada");
}

const feedbackContainer: Container = new CosmosClient(cosmosConnectionString)
	.database("novatech")
	.container("feedbacks");

function withCors(response: HttpResponseInit): HttpResponseInit {
	return {
		...response,
		headers: {
			...corsHeaders,
			...(response.headers ?? {})
		}
	};
}

export async function feedbackHandler(request: HttpRequest, _context: InvocationContext): Promise<HttpResponseInit> {
	if (request.method === "OPTIONS") {
		return withCors({
			status: 200,
			headers: corsHeaders
		});
	}

	if (request.method !== "POST") {
		return withCors({
			status: 405,
			jsonBody: {
				error: "Method Not Allowed"
			}
		});
	}

	let body: unknown;

	try {
		body = await request.json();
	} catch (error) {
		logger.warn(
			{
				method: request.method,
				path: request.url,
				error
			},
			"malformed feedback JSON body"
		);

		return withCors({
			status: 400,
			jsonBody: {
				error: "Malformed JSON body"
			}
		});
	}

	const parsed = feedbackRequestSchema.safeParse(body);

	if (!parsed.success) {
		logger.warn(
			{
				method: request.method,
				path: request.url,
				details: parsed.error.issues
			},
			"feedback request validation failed"
		);

		return withCors({
			status: 400,
			jsonBody: {
				error: "Invalid request body",
				details: parsed.error.issues
			}
		});
	}

	const feedback: FeedbackRecord = {
		...parsed.data,
		timestamp: new Date().toISOString()
	};

	try {
		await feedbackContainer.items.create(feedback);

		logger.info(
			{
				queryId: feedback.queryId,
				rating: feedback.rating
			},
			"feedback persisted"
		);

		return withCors({
			status: 201,
			jsonBody: {
				ok: true
			}
		});
	} catch (error) {
		logger.error(
			{
				error,
				queryId: feedback.queryId
			},
			"failed to persist feedback"
		);

		return withCors({
			status: 502,
			jsonBody: {
				error: "Falha ao salvar feedback"
			}
		});
	}
}

app.http("feedback", {
	methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
	authLevel: "anonymous",
	route: "feedback",
	handler: feedbackHandler
});
