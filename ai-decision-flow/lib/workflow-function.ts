import { inngest } from "@/lib/inngest";
import { askLLM } from "@/lib/llm";
import { WorkflowGraph, WorkflowEdge, ExecutionLog } from "@/lib/types";

export const runWorkflow = inngest.createFunction(
  { id: "run-workflow", triggers: [{ event: "workflow/run" }] },
  async ({ event, step }) => {
    const { graph, startNodeId, inputContext } = event.data as {
      graph: WorkflowGraph;
      startNodeId: string;
      inputContext: string;
    };

    const logs: ExecutionLog[] = [];
    const path: string[] = [];
    let currentNodeId: string | null = startNodeId;

    while (currentNodeId) {
      const node = graph.nodes.find((n) => n.id === currentNodeId);
      if (!node) break;

      path.push(currentNodeId);

      const logId = `log-${Date.now()}-${currentNodeId}`;
      const startTime = Date.now();

      const result: "YES" | "NO" | null = await step.run(`decide-${currentNodeId}`, async () => {
        const prompt = `${node.data.prompt}\n\nContext: ${inputContext}`;
        return await askLLM(prompt);
      });

      const durationMs = Date.now() - startTime;

      logs.push({
        id: logId,
        nodeId: currentNodeId,
        nodeLabel: node.data.label,
        prompt: node.data.prompt,
        result,
        timestamp: new Date().toISOString(),
        durationMs,
      });

      const edge: WorkflowEdge | undefined = graph.edges.find(
        (e: WorkflowEdge): boolean => e.source === currentNodeId && e.type === (result === "YES" ? "yes" : "no")
      );

      currentNodeId = edge?.target ?? null;
    }

    return { logs, path, completed: true };
  }
);

export const functions = [runWorkflow];
