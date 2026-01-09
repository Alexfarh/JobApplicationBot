"use client"

import * as React from "react"
import { Loader2, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"

export interface IngestJobsDialogProps {
  onJobsIngested?: () => void
}

export function IngestJobsDialog({ onJobsIngested }: IngestJobsDialogProps) {
  const [open, setOpen] = React.useState(false)
  const [isLoading, setIsLoading] = React.useState(false)
  const [results, setResults] = React.useState<Record<string, number> | null>(null)
  const [error, setError] = React.useState("")
  const { toast } = useToast()

  const handleIngestJobs = async () => {
    setIsLoading(true)
    setError("")
    setResults(null)

    try {
      const response = await fetch("/api/jobs/ingest", {
        method: "POST",
        credentials: "include",
      })

      if (!response.ok) {
        throw new Error("Failed to ingest jobs")
      }

      const data = await response.json()
      setResults(data)
      toast({
        title: "Jobs ingested successfully!",
        description: `Ingested jobs from ${Object.keys(data).length} companies.`,
      })

      // Call callback to refresh jobs list
      onJobsIngested?.()
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to ingest jobs"
      setError(message)
      toast({
        title: "Ingestion failed",
        description: message,
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          className="bg-purple-600 hover:bg-purple-700 text-white"
          disabled={isLoading}
        >
          <Zap className="w-4 h-4 mr-2" />
          Ingest Jobs
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-slate-900 border-slate-700">
        <DialogHeader>
          <DialogTitle>Ingest Jobs from Target Companies</DialogTitle>
          <DialogDescription>
            This will search for job postings from your target companies and add them to your job list.
            Based on your profile preferences (location, job type, etc.)
          </DialogDescription>
        </DialogHeader>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {results && (
          <div className="space-y-2">
            <h3 className="font-semibold text-white">Ingestion Results:</h3>
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {Object.entries(results).map(([company, count]) => (
                <div key={company} className="flex justify-between text-sm text-slate-300">
                  <span>{company}</span>
                  <Badge variant="secondary" className="bg-green-500/20 text-green-300">
                    {count} jobs
                  </Badge>
                </div>
              ))}
            </div>
            <div className="text-sm text-slate-400 pt-2">
              Total jobs ingested: {Object.values(results).reduce((a, b) => a + b, 0)}
            </div>
          </div>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={isLoading}
          >
            {results ? "Done" : "Cancel"}
          </Button>
          {!results && (
            <Button
              onClick={handleIngestJobs}
              disabled={isLoading}
              className="bg-purple-600 hover:bg-purple-700 text-white"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Ingesting...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 mr-2" />
                  Start Ingestion
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
