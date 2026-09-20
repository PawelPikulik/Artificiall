"use client";

import { ExecutionLog, ExecutionState } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface ExecutionPanelProps {
  currentExecution: ExecutionState | null;
  history: ExecutionState[];
}

function LogRow({ log, index }: { log: ExecutionLog; index: number }) {
  return (
    <div className="border-b py-2 last:border-b-0">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs text-muted-foreground">#{index + 1}</span>
        <span className="text-sm font-medium">{log.nodeLabel}</span>
        {log.result && (
          <Badge
            className={
              log.result === "YES"
                ? "bg-emerald-600 text-white"
                : "bg-rose-600 text-white"
            }
          >
            {log.result}
          </Badge>
        )}
        {log.durationMs && (
          <span className="text-xs text-muted-foreground ml-auto">
            {log.durationMs}ms
          </span>
        )}
      </div>
      <p className="text-xs text-muted-foreground line-clamp-2">{log.prompt}</p>
      {log.error && (
        <p className="text-xs text-rose-500 mt-1">{log.error}</p>
      )}
    </div>
  );
}

export default function ExecutionPanel({ currentExecution, history }: ExecutionPanelProps) {
  const formatTime = (iso: string | null) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleTimeString();
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Execution</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden p-0">
        <Tabs defaultValue="current" className="h-full flex flex-col">
          <TabsList className="mx-3 mt-0 mb-2">
            <TabsTrigger value="current" className="text-xs">
              Current
            </TabsTrigger>
            <TabsTrigger value="history" className="text-xs">
              History ({history.length})
            </TabsTrigger>
          </TabsList>
          <TabsContent value="current" className="flex-1 overflow-hidden m-0">
            <ScrollArea className="h-full px-3">
              {currentExecution?.isRunning && (
                <div className="flex items-center gap-2 py-2 text-xs text-amber-600">
                  <span className="animate-spin inline-block w-3 h-3 border-2 border-amber-600 border-t-transparent rounded-full" />
                  Running node: {currentExecution.currentNodeId}
                </div>
              )}
              {currentExecution?.logs.length === 0 && !currentExecution?.isRunning && (
                <p className="text-xs text-muted-foreground py-4">
                  No execution yet. Build a workflow and click Run.
                </p>
              )}
              {currentExecution?.logs.map((log, i) => (
                <LogRow key={log.id} log={log} index={i} />
              ))}
              {currentExecution?.endTime && (
                <div className="text-xs text-muted-foreground py-2">
                  Completed at {formatTime(currentExecution.endTime)}
                </div>
              )}
            </ScrollArea>
          </TabsContent>
          <TabsContent value="history" className="flex-1 overflow-hidden m-0">
            <ScrollArea className="h-full px-3">
              {history.length === 0 ? (
                <p className="text-xs text-muted-foreground py-4">
                  No past executions.
                </p>
              ) : (
                history
                  .slice()
                  .reverse()
                  .map((exec, i) => (
                    <div key={i} className="border-b py-2 last:border-b-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium">
                          {formatTime(exec.startTime)}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {exec.logs.length} steps
                        </Badge>
                      </div>
                      <div className="flex gap-1 mt-1 flex-wrap">
                        {exec.logs.map((l) => (
                          <span
                            key={l.id}
                            className={`text-[10px] px-1.5 py-0.5 rounded ${
                              l.result === "YES"
                                ? "bg-emerald-100 text-emerald-700"
                                : l.result === "NO"
                                  ? "bg-rose-100 text-rose-700"
                                  : "bg-slate-100 text-slate-700"
                            }`}
                          >
                            {l.result}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))
              )}
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
