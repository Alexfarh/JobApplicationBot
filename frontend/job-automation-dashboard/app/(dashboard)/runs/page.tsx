"use client"

import { useRuns, useDeleteRun, useStartRun } from "@/lib/hooks/use-api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { CreateRunDialog } from "@/components/create-run-dialog"
import { Trash2, Play, Eye, Loader2 } from "lucide-react"
import Link from "next/link"
import { formatDistanceToNow } from "date-fns"
import { useToast } from "@/hooks/use-toast"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"


export default function RunsPage() {
  const { data: runsData, isLoading } = useRuns()
  const runs = Array.isArray(runsData?.runs) ? runsData.runs : []
  const deleteRun = useDeleteRun()
  const startRun = useStartRun()
  const { toast } = useToast()

  const handleDelete = async (id: string, name: string) => {
    try {
      await deleteRun.mutateAsync(id)
      toast({
        title: "Run deleted",
        description: `${name} has been deleted.`,
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete run.",
        variant: "destructive",
      })
    }
  }

  const handleStart = async (id: string, name: string) => {
    try {
      await startRun.mutateAsync(id)
      toast({
        title: "Run started",
        description: `${name} is now running.`,
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to start run.",
        variant: "destructive",
      })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Application Runs</h1>
          <p className="text-muted-foreground">Manage your job application batches</p>
        </div>
        <CreateRunDialog />
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : runs && runs.length > 0 ? (
        <div className="grid gap-4">
          {runs.map((run) => (
            <Card key={run.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-xl">{run.name}</CardTitle>
                    {run.description && <p className="text-sm text-muted-foreground">{run.description}</p>}
                    <p className="text-xs text-muted-foreground">
                      Created {formatDistanceToNow(new Date(run.created_at.endsWith('Z') ? run.created_at : run.created_at + 'Z'), { addSuffix: true })}
                    </p>
                  </div>
                  <Badge variant={run.status === "running" ? "default" : "outline"}>
                    {run.status === "running" && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                    {run.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary">Queued: {run.queued_tasks}</Badge>
                    <Badge variant="secondary" className="animate-pulse-subtle">
                      Running: {run.running_tasks}
                    </Badge>
                    <Badge variant="default" className="bg-green-600">
                      Submitted: {run.submitted_tasks}
                    </Badge>
                    <Badge variant="destructive">Failed: {run.failed_tasks}</Badge>
                    <Badge variant="outline">Rejected: {run.rejected_tasks}</Badge>
                  </div>

                  <div className="flex gap-2">
                    <Button asChild size="sm" variant="outline">
                      <Link href={`/runs/${run.id}`}>
                        <Eye className="mr-2 h-4 w-4" />
                        View Details
                      </Link>
                    </Button>
                    {run.status === "created" && (
                      <Button size="sm" onClick={() => handleStart(run.id, run.name)}>
                        <Play className="mr-2 h-4 w-4" />
                        Start Run
                      </Button>
                    )}
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button size="sm" variant="destructive">
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This will permanently delete {run.name} and all associated tasks.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={() => handleDelete(run.id, run.name)}>Delete</AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
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
              <h3 className="mb-2 text-lg font-medium">No runs yet</h3>
              <p className="mb-4 text-sm text-muted-foreground">
                Create your first application run to automate job applications
              </p>
              <CreateRunDialog />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
