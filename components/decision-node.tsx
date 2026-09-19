"use client";

import { memo, useCallback, useState } from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { DecisionNodeData } from "@/lib/types";

function DecisionNode({ id, data, selected }: NodeProps) {
  const nodeData = data as unknown as DecisionNodeData;
  const [isEditing, setIsEditing] = useState(false);
  const [label, setLabel] = useState(nodeData.label);
  const [prompt, setPrompt] = useState(nodeData.prompt);

  const handleBlur = useCallback(() => {
    setIsEditing(false);
    const onUpdate = (data as unknown as { onUpdate?: (id: string, data: { label: string; prompt: string }) => void }).onUpdate;
    onUpdate?.(id, { label, prompt });
  }, [id, label, prompt, data]);

  const statusColor =
    nodeData.status === "running"
      ? "bg-amber-500"
      : nodeData.status === "success"
        ? "bg-emerald-500"
        : nodeData.status === "error"
          ? "bg-rose-500"
          : "bg-slate-500";

  const resultBadge =
    nodeData.result === "YES" ? (
      <Badge className="bg-emerald-600 text-white">YES</Badge>
    ) : nodeData.result === "NO" ? (
      <Badge className="bg-rose-600 text-white">NO</Badge>
    ) : null;

  return (
    <Card
      className={`w-64 shadow-lg transition-all duration-200 ${
        selected ? "ring-2 ring-primary" : ""
      } ${nodeData.status === "running" ? "animate-pulse" : ""}`}
    >
      <CardHeader className="pb-2 pt-3 px-3 flex flex-row items-center gap-2">
        <div className={`w-3 h-3 rounded-full ${statusColor}`} />
        {isEditing ? (
          <Input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            onBlur={handleBlur}
            autoFocus
            className="h-7 text-sm font-semibold"
          />
        ) : (
          <div
            className="text-sm font-semibold cursor-text truncate flex-1"
            onClick={() => setIsEditing(true)}
            title="Click to edit label"
          >
            {nodeData.label}
          </div>
        )}
        {resultBadge}
      </CardHeader>
      <CardContent className="px-3 pb-3 pt-0">
        {isEditing ? (
          <Textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onBlur={handleBlur}
            autoFocus
            className="text-xs min-h-[60px]"
            placeholder="Enter the decision prompt..."
          />
        ) : (
          <p
            className="text-xs text-muted-foreground line-clamp-3 cursor-text"
            onClick={() => setIsEditing(true)}
            title="Click to edit prompt"
          >
            {nodeData.prompt || "Click to add a decision prompt..."}
          </p>
        )}
      </CardContent>
      <Handle
        type="target"
        position={Position.Top}
        className="w-3 h-3 bg-slate-400"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="yes"
        className="w-3 h-3 !bg-emerald-500"
        style={{ left: "30%" }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="no"
        className="w-3 h-3 !bg-rose-500"
        style={{ left: "70%" }}
      />
    </Card>
  );
}

export default memo(DecisionNode);
