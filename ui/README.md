# Learning Agent UI

Learning Agents are AI agents that improve from experience and can handle tasks of varying complexity. This UI is intended to be used alongside the backend agent server in this repository.

If the concept is new to you, check out these videos!
Previously referenced videos on “Deep Agents” remain useful background:
- What are Deep Agents? https://www.youtube.com/watch?v=433SmtTc0TA
- Implementing Deep Agents: https://www.youtube.com/watch?v=TTMYJAw5tiA&t=701s


And check out this [video](https://youtu.be/0CE_BhdnZZI) for a walkthrough of this UI.

### Connecting to a Local LangGraph Server

Create a `.env.local` file and set two variables

```env
NEXT_PUBLIC_DEPLOYMENT_URL="http://127.0.0.1:2024" # Or your server URL
NEXT_PUBLIC_AGENT_ID=<your agent ID from langgraph.json>
```

### Connecting to a Production LangGraph Deployment on LGP

Create a `.env.local` file and set three variables

```env
NEXT_PUBLIC_DEPLOYMENT_URL="your agent server URL"
NEXT_PUBLIC_AGENT_ID=<your agent ID from langgraph.json>
NEXT_PUBLIC_LANGSMITH_API_KEY=<langsmith-api-key>
```



Once you have your environment variables set, install all dependencies and run your app.

```bash
npm install
npm run dev
```


Open [http://localhost:3000](http://localhost:3000) to test out your deep agent!
