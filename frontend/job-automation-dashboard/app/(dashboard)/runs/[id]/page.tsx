"use client"

import { useParams } from "next/navigation"
import { useRun, useTasks, useResumeTask, useCompleteRun } from "@/lib/hooks/use-api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { TaskStateBadge } from "@/components/task-state-badge"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Loader2, CheckCircle, AlertCircle, RefreshCw } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { useToast } from "@/hooks/use-toast"
import type { TaskState } from "@/lib/api"

export default function RunDetailPage() {
  const params = useParams()
  const runId = params.id as string
  const { data: run, isLoading } = useRun(runId, 5000)
  const { data: tasks } = useTasks({ run_id: runId })
  const resumeTask = useResumeTask()
  const completeRun = useCompleteRun()
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

  const handleComplete = async () => {
    try {
      await completeRun.mutateAsync(runId)
      toast({
        title: "Run completed",
        description: "Application run has been marked as completed.",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to complete run.",
        variant: "destructive",
      })
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!run) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold">Run not found</h2>
      </div>
    )
  }

  const tasksByState = tasks?.reduce(
    (acc, task) => {
      if (!acc[task.state]) acc[task.state] = []
      acc[task.state].push(task)
      return acc
    },
    {} as Record<TaskState, typeof tasks>,
  )

  const states: TaskState[] = [
    "QUEUED",
    "RUNNING",
    "NEEDS_AUTH",
    "NEEDS_USER",
    "PENDING_APPROVAL",
    "SUBMITTED",
    "FAILED",
    "REJECTED",
    "EXPIRED",
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{run.name}</h1>
            <Badge variant={run.status === "running" ? "default" : "outline"}>
              {run.status === "running" && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
              {run.status}
            </Badge>
          </div>
          {run.description && <p className="text-muted-foreground">{run.description}</p>}
          <p className="text-sm text-muted-foreground">
            Created {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
          </p>
        </div>
        <div className="flex gap-2">
          {run.status === "running" && (
            <Button onClick={handleComplete}>
              <CheckCircle className="mr-2 h-4 w-4" />
              Complete Run
            </Button>
          )}
        </div>
      </div>

      {/* Progress Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Progress Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <Badge variant="secondary">Queued: {run.queued_tasks}</Badge>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="animate-pulse-subtle">
                Running: {run.running_tasks}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="default" className="bg-green-600">
                Submitted: {run.submitted_tasks}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="destructive">Failed: {run.failed_tasks}</Badge>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">Rejected: {run.rejected_tasks}</Badge>
            </div>
          </div>
          <div className="mt-4">
            <div className="flex justify-between text-sm text-muted-foreground mb-2">
              <span>Total Progress</span>
              <span>
                {run.submitted_tasks + run.rejected_tasks}/{run.total_tasks}
              </span>
            </div>
            <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all"
                style={{
                  width: `${
                    run.total_tasks > 0 ? ((run.submitted_tasks + run.rejected_tasks) / run.total_tasks) * 100 : 0
                  }%`,
                }}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Task Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Tasks by State</CardTitle>
        </CardHeader>
        <CardContent>
          <Accordion type="multiple" className="w-full">
            {states.map((state) => {
              const stateTasks = tasksByState?.[state] || []
              if (stateTasks.length === 0) return null

              return (
                <AccordionItem key={state} value={state}>
                  <AccordionTrigger>
                    <div className="flex items-center gap-3">
                      <TaskStateBadge state={state} />
                      <span className="text-muted-foreground">({stateTasks.length})</span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-3">
                      {stateTasks.map((task) => (
                        <Card key={task.id}>
                          <CardContent className="pt-6">
                            <div className="flex items-start justify-between">
                              <div className="space-y-1">
                                <p className="font-medium">{task.job?.job_title || "Unknown Job"}</p>
                                <p className="text-sm text-muted-foreground">
                                  {task.job?.company_name || "Unknown Company"}
                                </p>
                                {task.job?.location_text && (
                                  <p className="text-xs text-muted-foreground">{task.job.location_text}</p>
                                )}
                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                  <span>Attempts: {task.attempt_count}</span>
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
                                {(state === "FAILED" || state === "EXPIRED") && (
                                  <Button size="sm" variant="outline" onClick={() => handleResume(task.id, state)}>
                                    <RefreshCw className="mr-2 h-4 w-4" />
                                    Resume
                                  </Button>
                                )}
                                {state === "PENDING_APPROVAL" && <Button size="sm">Review & Approve</Button>}
                                {state === "NEEDS_AUTH" && (
                                  <Button size="sm" variant="destructive">
                                    Open Browser
                                  </Button>
                                )}
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )
            })}
          </Accordion>
        </CardContent>
      </Card>
    </div>
  )
}
