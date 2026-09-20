import { WorkflowGraph, ExecutionState } from "@/lib/types";

const WORKFLOW_KEY = "ai-decision-workflow";
const EXECUTIONS_KEY = "ai-decision-executions";

export function saveWorkflow(graph: WorkflowGraph) {
  localStorage.setItem(WORKFLOW_KEY, JSON.stringify(graph));
}

export function loadWorkflow(): WorkflowGraph | null {
  const raw = localStorage.getItem(WORKFLOW_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as WorkflowGraph;
  } catch {
    return null;
  }
}

export function saveExecutions(executions: ExecutionState[]) {
  localStorage.setItem(EXECUTIONS_KEY, JSON.stringify(executions.slice(-20)));
}

export function loadExecutions(): ExecutionState[] {
  const raw = localStorage.getItem(EXECUTIONS_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as ExecutionState[];
  } catch {
    return [];
  }
}

export function exportWorkflow(graph: WorkflowGraph): string {
  return JSON.stringify(graph, null, 2);
}

export function importWorkflow(json: string): WorkflowGraph | null {
  try {
    return JSON.parse(json) as WorkflowGraph;
  } catch {
    return null;
  }
}
