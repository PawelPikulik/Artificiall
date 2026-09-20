export interface DecisionNodeData {
  label: string;
  prompt: string;
  result?: "YES" | "NO" | null;
  status?: "idle" | "running" | "success" | "error";
  onUpdate?: (id: string, data: { label: string; prompt: string }) => void;
  [key: string]: unknown;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type: "yes" | "no";
  label?: string;
}

export interface WorkflowNode {
  id: string;
  type: "decision";
  position: { x: number; y: number };
  data: DecisionNodeData;
}

export interface WorkflowGraph {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface ExecutionLog {
  id: string;
  nodeId: string;
  nodeLabel: string;
  prompt: string;
  result: "YES" | "NO" | null;
  timestamp: string;
  error?: string;
  durationMs?: number;
}

export interface ExecutionState {
  isRunning: boolean;
  currentNodeId: string | null;
  logs: ExecutionLog[];
  path: string[];
  startTime: string | null;
  endTime: string | null;
}
