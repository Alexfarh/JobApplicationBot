"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useRuns, useJobs, useTasks } from "@/lib/hooks/use-api"
import { useProfile } from "@/lib/hooks/use-profile"
import type { ApplicationRun, JobPosting, ApplicationTask } from "@/lib/api"
import { Layers, Briefcase, TrendingUp, Activity } from "lucide-react"
import { CreateRunDialog } from "@/components/create-run-dialog"
import { CreateJobDialog } from "@/components/create-job-dialog"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { formatDistanceToNow } from "date-fns"
import { useEffect, useState } from "react"

export default function DashboardPage() {
  const { data: profile, isLoading: profileLoading, error: profileError } = useProfile();
    // Hydration-safe client flag
    const [isClient, setIsClient] = useState(false);
    useEffect(() => setIsClient(true), []);

  const {
    data: runsRaw,
    error: runsError,
    isLoading: runsLoading,
  } = useRuns();
  const {
    data: jobsRaw,
    error: jobsError,
    isLoading: jobsLoading,
  } = useJobs();
  const {
    data: tasksRaw,
    error: tasksError,
    isLoading: tasksLoading,
  } = useTasks();

  // Defensive guards for all data
  const runs: ApplicationRun[] = Array.isArray(runsRaw?.runs) ? runsRaw.runs : [];
  const jobs: JobPosting[] = Array.isArray(jobsRaw) ? jobsRaw : [];
  const tasks: ApplicationTask[] = Array.isArray(tasksRaw) ? tasksRaw : [];

  // Error Handling
  if (runsError || jobsError || tasksError || profileError) {
    return (
      <div className="p-8">
        <div className="mb-4 p-4 bg-red-100 text-red-800 rounded">
          {runsError && <div>Failed to load runs: {String(runsError)}</div>}
          {jobsError && <div>Failed to load jobs: {String(jobsError)}</div>}
          {tasksError && <div>Failed to load tasks: {String(tasksError)}</div>}
          {profileError && <div>Failed to load profile: {String(profileError)}</div>}
        </div>
      </div>
    );
  }

  // Loading State
  if (runsLoading || jobsLoading || tasksLoading || profileLoading) {
    return (
      <div className="p-8">
        <div className="mb-4 p-4 bg-blue-100 text-blue-800 rounded">Loading data...</div>
      </div>
    );
  }

  // Types now imported from API

  const activeRun = runs.find((r: ApplicationRun) => r && r.status === "running");
  const totalSubmitted = runs.reduce((acc: number, r: ApplicationRun) => acc + (r?.submitted_tasks || 0), 0);
  const totalTasks = runs.reduce((acc: number, r: ApplicationRun) => acc + (r?.total_tasks || 0), 0);
  const successRate = totalTasks > 0 ? ((totalSubmitted / totalTasks) * 100).toFixed(1) : "0";
  const runsLength = runs.length;
  const activeRunsCount = runs.filter((r: ApplicationRun) => r && r.status === "running").length;
  const notAppliedJobs = jobs.filter((j: JobPosting) => j && !j.has_been_applied_to).length;

  // Example: count of all tasks
  const totalTasksCount = Array.isArray(tasks) ? tasks.length : 0;
  // Example: count of running tasks
  const runningTasksCount = Array.isArray(tasks) ? tasks.filter((t: ApplicationTask) => t && t.state === "RUNNING").length : 0;
  // Example: recent tasks (last 5)
  const recentTasks = Array.isArray(tasks) ? tasks.slice(0, 5) : [];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">Monitor your job application automation</p>
        </div>
        <div className="flex gap-2">
          <CreateJobDialog />
          <CreateRunDialog />
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
            <Layers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runsLength}</div>
            <p className="text-xs text-muted-foreground">
              {activeRunsCount} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Jobs Ingested</CardTitle>
            <Briefcase className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{jobs.length}</div>
            <p className="text-xs text-muted-foreground">
              {notAppliedJobs} not applied
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{successRate}%</div>
            <p className="text-xs text-muted-foreground">
              {totalSubmitted} of {totalTasks} submitted
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Run</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeRun ? activeRun.running_tasks : 0}</div>
            <p className="text-xs text-muted-foreground">{activeRun ? "tasks running" : "No active run"}</p>
          </CardContent>
        </Card>
      </div>

      {/* Task Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Tasks Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-2">
            <div>Total Tasks: <span className="font-bold">{totalTasksCount}</span></div>
            <div>Running Tasks: <span className="font-bold">{runningTasksCount}</span></div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Tasks */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Tasks</CardTitle>
        </CardHeader>
        <CardContent>
          {tasks.length > 0 ? (
            <div className="space-y-2">
              {recentTasks.map((task: ApplicationTask) => {
                const job = jobs.find((j) => j.id === task.job_id);
                return (
                  <div key={task.id} className="flex items-center justify-between border-b border-border pb-2 last:border-0 last:pb-0">
                    <div>
                      <p className="font-medium">{job ? job.job_title : task.id}</p>
                      <p className="text-xs text-muted-foreground">State: {task.state}</p>
                    </div>
                    <div className="text-xs text-muted-foreground">{task.queued_at ? new Date(task.queued_at).toLocaleString() : ""}</div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="py-4 text-center text-muted-foreground">No tasks found</div>
          )}
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Runs</CardTitle>
        </CardHeader>
        <CardContent>
          {runs.length > 0 ? (
            <div className="space-y-4">
              {runs.slice(0, 5).map((run) => (
                <div
                  key={run.id}
                  className="flex items-center justify-between border-b border-border pb-4 last:border-0 last:pb-0"
                >
                  <div className="space-y-1">
                    <p className="font-medium">{run.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {isClient ? (
                        <>Created {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}</>
                      ) : null}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right text-sm">
                      <p className="font-medium">
                        {run.submitted_tasks}/{run.total_tasks}
                      </p>
                      <p className="text-muted-foreground">submitted</p>
                    </div>
                    <Button asChild variant="outline" size="sm">
                      <Link href={`/runs/${run.id}`}>View</Link>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Layers className="mb-2 h-12 w-12 text-muted-foreground" />
              <h3 className="mb-1 text-lg font-medium">No runs yet</h3>
              <p className="mb-4 text-sm text-muted-foreground">Create your first application run to get started</p>
              <CreateRunDialog />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
