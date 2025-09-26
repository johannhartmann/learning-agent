import { NextRequest } from "next/server";
import {
  CopilotRuntime,
  EmptyAdapter,
  LangGraphAgent,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";

// Disable Copilot Cloud telemetry; this UI only talks to the self-hosted runtime.
process.env.COPILOTKIT_TELEMETRY_DISABLED = "true";
process.env.DO_NOT_TRACK = "1";

// In Docker, always use the service name for inter-container communication
// The backend service is named "server" in docker-compose.yml
const deploymentUrl = "http://server:2024";
const graphId = process.env.NEXT_PUBLIC_AGENT_ID ?? process.env.AGENT_ID ?? "learning_agent";
const langsmithApiKey = process.env.LANGSMITH_API_KEY ?? process.env.NEXT_PUBLIC_LANGSMITH_API_KEY;

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
