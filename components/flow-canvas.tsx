"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  Connection,
  Edge,
  Node,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import DecisionNode from "@/components/decision-node";
import ExecutionPanel from "@/components/execution-panel";
import {
  saveWorkflow,
  loadWorkflow,
  saveExecutions,
  loadExecutions,
  exportWorkflow,
  importWorkflow,
} from "@/lib/workflow-store";
import { WorkflowNode, WorkflowEdge, ExecutionState, ExecutionLog } from "@/lib/types";

const nodeTypes = { decision: DecisionNode };

function generateId() {
  return `node-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
}

const defaultNodes: WorkflowNode[] = [
  {
    id: "start",
    type: "decision",
    position: { x: 250, y: 50 },
    data: { label: "Is this a support request?", prompt: "Is this a support request?" },
  },
  {
    id: "support",
    type: "decision",
    position: { x: 100, y: 250 },
    data: { label: "Support Node", prompt: "Route to support team" },
  },
  {
    id: "sales",
    type: "decision",
    position: { x: 400, y: 250 },
    data: { label: "Sales Node", prompt: "Route to sales team" },
  },
];

const defaultEdges: WorkflowEdge[] = [
  {
    id: "e-start-support",
    source: "start",
    target: "support",
    type: "yes",
    label: "YES",
  },
  {
    id: "e-start-sales",
    source: "start",
    target: "sales",
    type: "no",
    label: "NO",
  },
];

export default function FlowCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [execution, setExecution] = useState<ExecutionState | null>(null);
  const [history, setHistory] = useState<ExecutionState[]>([]);
  const [inputContext, setInputContext] = useState("");
  const [importJson, setImportJson] = useState("");
  const [importError, setImportError] = useState<string | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    const saved = loadWorkflow();
    if (saved) {
      setNodes(saved.nodes as Node[]);
      setEdges(saved.edges as unknown as Edge[]);
    } else {
      setNodes(defaultNodes as Node[]);
      setEdges(defaultEdges as unknown as Edge[]);
    }
    setHistory(loadExecutions());
  }, []);

  // Save to localStorage when nodes/edges change
  useEffect(() => {
    if (nodes.length > 0) {
      saveWorkflow({
        nodes: nodes as WorkflowNode[],
        edges: edges as unknown as WorkflowEdge[],
      });
    }
  }, [nodes, edges]);

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return;
      const edgeType = (connection.sourceHandle as "yes" | "no") || "yes";
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            id: `e-${connection.source}-${connection.target}`,
            type: edgeType,
            label: edgeType.toUpperCase(),
            markerEnd: { type: MarkerType.ArrowClosed },
            style: {
              stroke: edgeType === "yes" ? "#10b981" : "#f43f5e",
              strokeWidth: 2,
            },
          },
          eds
        )
      );
    },
    [setEdges]
  );

  const onNodeUpdate = useCallback(
    (id: string, data: { label: string; prompt: string }) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === id
            ? { ...n, data: { ...n.data, label: data.label, prompt: data.prompt } }
            : n
        )
      );
    },
    [setNodes]
  );

  const addNode = useCallback(() => {
    const id = generateId();
    const newNode: Node = {
      id,
      type: "decision",
      position: { x: 250 + Math.random() * 100, y: 200 + Math.random() * 100 },
      data: {
        label: `Decision ${nodes.length + 1}`,
        prompt: "Enter your decision prompt...",
        onUpdate: onNodeUpdate,
      },
    };
    setNodes((nds) => [...nds, newNode]);
  }, [nodes.length, onNodeUpdate, setNodes]);

  // Attach onUpdate to all nodes so they can edit themselves
  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) =>
        !n.data.onUpdate ? { ...n, data: { ...n.data, onUpdate: onNodeUpdate } } : n
      )
    );
  }, [onNodeUpdate]);

  const resetNodeStatus = useCallback(() => {
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: { ...n.data, status: "idle", result: null },
      }))
    );
    setEdges((eds) =>
      eds.map((e) => ({
        ...e,
        style: {
          ...e.style,
          opacity: 1,
          strokeWidth: 2,
        },
      }))
    );
  }, [setNodes, setEdges]);

  const runWorkflow = useCallback(async () => {
    if (!inputContext.trim()) {
      alert("Please enter input context before running the workflow.");
      return;
    }

    resetNodeStatus();

    const startNode = nodes.find((n) => n.id === "start") || nodes[0];
    if (!startNode) {
      alert("No nodes to execute.");
      return;
    }

    const newExecution: ExecutionState = {
      isRunning: true,
      currentNodeId: startNode.id,
      logs: [],
      path: [],
      startTime: new Date().toISOString(),
      endTime: null,
    };
    setExecution(newExecution);

    const logs: ExecutionLog[] = [];
    const path: string[] = [];
    let currentId: string | null = startNode.id;

    try {
      while (currentId) {
        const node = nodes.find((n) => n.id === currentId);
        if (!node) break;

        path.push(currentId);
        setExecution((prev) =>
          prev ? { ...prev, currentNodeId: currentId } : prev
        );

        setNodes((nds) =>
          nds.map((n) =>
            n.id === currentId ? { ...n, data: { ...n.data, status: "running" } } : n
          )
        );

        // Call the API endpoint
        const response: Response = await fetch("/api/run-workflow", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            nodeId: currentId,
            prompt: node.data.prompt as string,
            context: inputContext,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const json = await response.json() as { result: "YES" | "NO"; durationMs: number };
        const result = json.result;
        const durationMs = json.durationMs;

        const log: ExecutionLog = {
          id: `log-${Date.now()}-${currentId}`,
          nodeId: currentId,
          nodeLabel: node.data.label as string,
          prompt: node.data.prompt as string,
          result,
          timestamp: new Date().toISOString(),
          durationMs,
        };
        logs.push(log);

        setNodes((nds) =>
          nds.map((n) =>
            n.id === currentId
              ? { ...n, data: { ...n.data, status: "success", result } }
              : n
          )
        );

        // Highlight edge
        const nextEdge = (edges as unknown as WorkflowEdge[]).find(
          (e: WorkflowEdge) => e.source === currentId && e.type === (result === "YES" ? "yes" : "no")
        );
        if (nextEdge) {
          setEdges((eds) =>
            eds.map((e: Edge) =>
              e.id === nextEdge.id
                ? {
                    ...e,
                    style: {
                      ...e.style,
                      strokeWidth: 4,
                      opacity: 1,
                    },
                    animated: true,
                  }
                : {
                    ...e,
                    style: { ...e.style, opacity: 0.3 },
                    animated: false,
                  }
            )
          );
        }

        currentId = nextEdge?.target ?? null;
      }
    } catch (err) {
      const error = err instanceof Error ? err.message : "Unknown error";
      logs.push({
        id: `log-${Date.now()}-error`,
        nodeId: currentId || "unknown",
        nodeLabel: "Error",
        prompt: "",
        result: null,
        timestamp: new Date().toISOString(),
        error,
      });
      setNodes((nds) =>
        nds.map((n) =>
          n.id === currentId
            ? { ...n, data: { ...n.data, status: "error" } }
            : n
        )
      );
    }

    const completedExecution: ExecutionState = {
      isRunning: false,
      currentNodeId: null,
      logs,
      path,
      startTime: newExecution.startTime,
      endTime: new Date().toISOString(),
    };

    setExecution(completedExecution);
    const newHistory = [...history, completedExecution];
    setHistory(newHistory);
    saveExecutions(newHistory);
  }, [nodes, edges, inputContext, history, resetNodeStatus, setNodes, setEdges, setExecution]);

  const handleExport = useCallback(() => {
    const json = exportWorkflow({
      nodes: nodes as WorkflowNode[],
      edges: edges as unknown as WorkflowEdge[],
    });
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "workflow.json";
    a.click();
    URL.revokeObjectURL(url);
  }, [nodes, edges]);

  const handleImport = useCallback(() => {
    setImportError(null);
    const graph = importWorkflow(importJson);
    if (!graph) {
      setImportError("Invalid JSON. Please paste a valid workflow export.");
      return;
    }
    setNodes(graph.nodes as Node[]);
    setEdges(graph.edges as unknown as Edge[]);
    setImportJson("");
  }, [importJson, setNodes, setEdges]);

  const handleClear = useCallback(() => {
    setNodes([]);
    setEdges([]);
  }, [setNodes, setEdges]);

  return (
    <div className="flex h-screen w-full">
      <div className="flex-1 flex flex-col">
        <div className="flex items-center gap-3 p-3 border-b bg-card">
          <h1 className="text-lg font-bold mr-4">AI Decision Flow</h1>
          <Button size="sm" onClick={addNode}>
            + Node
          </Button>
          <Button size="sm" variant="secondary" onClick={runWorkflow}>
            Run Workflow
          </Button>
          <Input
            placeholder="Input context for the workflow..."
            value={inputContext}
            onChange={(e) => setInputContext(e.target.value)}
            className="w-64 text-sm"
          />
          {execution?.isRunning && (
            <Badge variant="secondary" className="animate-pulse">
              Running...
            </Badge>
          )}
          <div className="ml-auto flex gap-2">
            <Button size="sm" variant="outline" onClick={handleExport}>
              Export
            </Button>
            <Dialog>
              <DialogTrigger render={<Button size="sm" variant="outline">Import</Button>} />
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Import Workflow</DialogTitle>
                </DialogHeader>
              <Textarea
                  placeholder="Paste workflow JSON here..."
                  value={importJson}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setImportJson(e.target.value)}
                  className="min-h-[200px] font-mono text-xs"
                />
                {importError && (
                  <p className="text-sm text-rose-500">{importError}</p>
                )}
                <Button onClick={handleImport}>Import</Button>
              </DialogContent>
            </Dialog>
            <Button size="sm" variant="ghost" onClick={handleClear}>
              Clear
            </Button>
          </div>
        </div>
        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            attributionPosition="bottom-left"
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>
      </div>
      <div className="w-80 border-l">
        <ExecutionPanel currentExecution={execution} history={history} />
      </div>
    </div>
  );
}

