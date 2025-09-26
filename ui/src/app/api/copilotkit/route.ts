import { NextRequest } from "next/server";
import {
  CopilotRuntime,
  EmptyAdapter,
  LangGraphAgent,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";

const deploymentUrl = process.env.NEXT_PUBLIC_DEPLOYMENT_URL ?? process.env.DEPLOYMENT_URL;
const graphId = process.env.NEXT_PUBLIC_AGENT_ID ?? process.env.AGENT_ID;
const langsmithApiKey = process.env.LANGSMITH_API_KEY ?? process.env.NEXT_PUBLIC_LANGSMITH_API_KEY;

if (!deploymentUrl) {
  throw new Error("Missing NEXT_PUBLIC_DEPLOYMENT_URL environment variable.");
}

if (!graphId) {
  throw new Error("Missing NEXT_PUBLIC_AGENT_ID environment variable.");
}

const agentKey = "learning_agent";

const runtime = new CopilotRuntime({
  agents: {
    [agentKey]: new LangGraphAgent({
      graphId,
      deploymentUrl,
      langsmithApiKey: langsmithApiKey ?? undefined,
      agentName: agentKey,
    }),
  },
});

const { handleRequest, GET, POST, OPTIONS } = copilotRuntimeNextJSAppRouterEndpoint({
  runtime,
  serviceAdapter: new EmptyAdapter(),
  endpoint: "/api/copilotkit",
});

export { GET, POST, OPTIONS };

export async function HEAD(request: NextRequest) {
  return handleRequest(request);
}
