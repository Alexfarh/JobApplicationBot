"use client"

import { useState } from "react"
import { useTasks, useResumeTask, useRuns } from "@/lib/hooks/use-api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { TaskStateBadge } from "@/components/task-state-badge"
import { Loader2, RefreshCw, AlertCircle, Filter } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { useToast } from "@/hooks/use-toast"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { TaskState } from "@/lib/api"


export default function TasksPage() {
  const [stateFilter, setStateFilter] = useState<string>("all")
  const [runFilter, setRunFilter] = useState<string>("all")

  const params =
    stateFilter === "all" && runFilter === "all"
      ? undefined
      : {
          state: stateFilter === "all" ? undefined : (stateFilter as TaskState),
          run_id: runFilter === "all" ? undefined : runFilter,
        }

  const { data: tasks, isLoading } = useTasks(params)
  const { data } = useRuns()
  const runs = data?.runs ?? []
  const resumeTask = useResumeTask()
  const { toast } = useToast()

  const handleResume = async (taskId: string, fromState: TaskState) => {
    try {
      await resumeTask.mutateAsync({ id: taskId, from_state: fromState })
      toast({
        title: "Task resumed",
        description: "Task has been resumed with priority boost.",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to resume task.",
        variant: "destructive",
      })
    }
  }

  const states: TaskState[] = [
    "QUEUED",
    "RUNNING",
    "NEEDS_AUTH",
    "NEEDS_USER",
    "PENDING_APPROVAL",
    "APPROVED",
    "SUBMITTED",
    "FAILED",
    "EXPIRED",
    "REJECTED",
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">All Tasks</h1>
        <p className="text-muted-foreground">View and manage tasks across all runs</p>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Select value={stateFilter} onValueChange={setStateFilter}>
              <SelectTrigger className="w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All States</SelectItem>
                {states.map((state) => (
                  <SelectItem key={state} value={state}>
                    {state}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={runFilter} onValueChange={setRunFilter}>
              <SelectTrigger className="w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Runs</SelectItem>
                {runs?.map((run) => (
                  <SelectItem key={run.id} value={run.id}>
                    {run.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Tasks List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : tasks && tasks.length > 0 ? (
        <div className="grid gap-4">
          {tasks.map((task) => (
            <Card key={task.id}>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <TaskStateBadge state={task.state} />
                      <h3 className="font-semibold">{task.job?.job_title || "Unknown Job"}</h3>
                    </div>
                    <p className="text-sm text-muted-foreground">{task.job?.company_name || "Unknown Company"}</p>
                    {task.job?.location_text && (
                      <p className="text-xs text-muted-foreground">{task.job.location_text}</p>
                    )}
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>Attempts: {task.attempt_count}</span>
                      <span>•</span>
                      <span>Priority: {task.priority}</span>
                      <span>•</span>
                      <span>
                        Last updated{" "}
                        {formatDistanceToNow(new Date(task.last_state_change_at), {
                          addSuffix: true,
                        })}
                      </span>
                    </div>
                    {task.last_error_message && (
                      <div className="mt-2 rounded-md bg-destructive/10 p-2">
                        <p className="text-sm text-destructive flex items-start gap-2">
                          <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                          <span>{task.last_error_message}</span>
                        </p>
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {(task.state === "FAILED" || task.state === "EXPIRED") && (
                      <Button size="sm" variant="outline" onClick={() => handleResume(task.id, task.state)}>
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Resume
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <div className="text-center">
              <h3 className="mb-2 text-lg font-medium">No tasks found</h3>
              <p className="text-sm text-muted-foreground">
                {stateFilter !== "all" || runFilter !== "all"
                  ? "Try adjusting your filters"
                  : "Create a run to generate tasks"}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
