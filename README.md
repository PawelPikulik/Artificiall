# AI Decision Flow

A visual workflow builder where each node is an AI decision step. Build a graph of YES/NO questions, connect them with conditional edges, and run the workflow through an LLM.

**Assignment**: BE-09 — Backend AI Engineering, Week 7  
**Stack**: Next.js 16, React Flow, Inngest, OpenAI SDK, shadcn/ui

## Features

- **Visual Canvas** — Drag-and-drop React Flow canvas with custom decision nodes
- **YES/NO Edges** — Connect nodes with conditional edges (green = YES, red = NO)
- **LLM Execution** — Each node sends its prompt + input context to OpenAI (gpt-4o-mini), which returns a strict YES/NO decision
- **Inngest Integration** — Server-side workflow function for durable execution
- **Execution Logs** — Side panel showing every step, result, timing, and traversal path
- **Save / Load** — Persist workflows to localStorage
- **Export / Import** — Share workflows as JSON
- **Visual State** — Nodes and edges highlight during execution (running → success → error)

## Quick Start

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Add your OpenAI API key**
   ```bash
   echo "OPENAI_API_KEY=sk-..." > .env.local
   ```

3. **Run the dev server**
   ```bash
   npm run dev
   ```

4. **Open** [http://localhost:3000](http://localhost:3000)

## Architecture

| File | Purpose |
|------|---------|
| `app/page.tsx` | Main page layout (canvas + execution panel) |
| `components/flow-canvas.tsx` | React Flow canvas, node/edge logic, execution runner |
| `components/decision-node.tsx` | Custom node UI with inline prompt editing |
| `components/execution-panel.tsx` | Execution logs, history tabs |
| `lib/types.ts` | TypeScript interfaces for nodes, edges, execution state |
| `lib/inngest.ts` | Inngest client instance |
| `lib/workflow-function.ts` | Inngest function definition (v4 API) |
| `lib/llm.ts` | OpenAI wrapper with strict YES/NO parsing |
| `lib/workflow-store.ts` | localStorage persistence helpers |
| `app/api/run-workflow/route.ts` | Per-node LLM API endpoint |
| `app/api/inngest/route.ts` | Inngest serve handler |

## Workflow JSON Format

```json
{
  "nodes": [
    {
      "id": "1",
      "type": "decision",
      "position": { "x": 250, "y": 50 },
      "data": { "label": "Is it urgent?", "prompt": "Is this request urgent? Reply YES or NO." }
    }
  ],
  "edges": [
    { "id": "e1-2", "source": "1", "target": "2", "type": "yes", "label": "YES" }
  ]
}
```

## Deliverables

- [x] React Flow canvas with YES/NO decision nodes
- [x] Editable prompts per node
- [x] Inngest workflow execution with LLM
- [x] Execution logs panel
- [x] Save / load / export / import workflows
- [x] Visual execution state (active nodes & edges)

## Notes

- The `npm run build` target compiles cleanly with TypeScript strict mode.
- Inngest v4.20.0 uses the 2-argument `createFunction(opts, handler)` API.
- The app defaults to a 3-node demo workflow on first load.
