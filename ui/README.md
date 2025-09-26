# Learning Agent UI

This Next.js app uses **CopilotKit** to render the LangGraph/DeepAgents assistant, share agent state, and surface learning artifacts. The UI exposes:

- A CopilotKit chat panel bound to the LangGraph agent
- A task list sourced from `state.todos`
- A learning dashboard that streams `state.memories`, `state.patterns`, and `state.learning_queue`
- An artifact gallery that renders sandbox files (markdown + images)

## Environment setup

Copy `.env.example` to `.env.local` and set the deployment values expected by the LangGraph backend:

```env
NEXT_PUBLIC_DEPLOYMENT_URL=http://127.0.0.1:2024
NEXT_PUBLIC_AGENT_ID=learning_agent
# Optional when using LangSmith hosted auth
NEXT_PUBLIC_LANGSMITH_API_KEY=ls__...
```

## Install & run

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to chat with the agent.

### What to expect

- The `/api/copilotkit` route bridges CopilotKit to your LangGraph deployment via the AG-UI protocol.
- Chat responses render in the CopilotKit window; todos, learning signals, and artifacts stream into the side panels in real time.
- Update the backend to emit additional state keys if you need to show more learning context in the UI.
