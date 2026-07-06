import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import pino from "pino";

import { queryRequestSchema } from "./validator.js";

const logger = pino({ name: "query-endpoint" });
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type"
};

function withCors(response: HttpResponseInit): HttpResponseInit {
  return {
    ...response,
    headers: {
      ...corsHeaders,
      ...(response.headers ?? {})
    }
  };
}

export async function queryHandler(request: HttpRequest, _context: InvocationContext): Promise<HttpResponseInit> {
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
      "malformed JSON body"
    );

    return withCors({
      status: 400,
      jsonBody: {
        error: "Malformed JSON body"
      }
    });
  }

  const result = queryRequestSchema.safeParse(body);

  if (!result.success) {
    logger.warn(
      {
        method: request.method,
        path: request.url,
        details: result.error.issues
      },
      "query request validation failed"
    );

    return withCors({
      status: 400,
      jsonBody: {
        error: "Invalid request body",
        details: result.error.issues
      }
    });
  }

  logger.info(
    {
      method: request.method,
      path: request.url,
      questionLength: result.data.question.length
    },
    "query request accepted"
  );

  return withCors({
    status: 200,
    jsonBody: {
      received: true
    }
  });
}

app.http("query", {
  methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
  authLevel: "anonymous",
  route: "query",
  handler: queryHandler
});
