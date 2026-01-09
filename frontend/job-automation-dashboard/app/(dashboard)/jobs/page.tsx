"use client"

import { useState, useMemo } from "react"
import { useJobs, useDeleteJob } from "@/lib/hooks/use-api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { CreateJobDialog } from "@/components/create-job-dialog"
import { IngestJobsDialog } from "@/components/ingest-jobs-dialog"
import { Trash2, ExternalLink, Loader2, Search, Filter } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
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

export default function JobsPage() {
  const [appliedFilter, setAppliedFilter] = useState<string>("all")
  const [workModeFilter, setWorkModeFilter] = useState<string>("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [page, setPage] = useState(0)
  const pageSize = 50

  const params = useMemo(() => {
    const p: any = {
      skip: page * pageSize,
      limit: pageSize,
    }
    if (appliedFilter !== "all") {
      p.applied = appliedFilter === "applied" ? true : false
    }
    if (workModeFilter !== "all") {
      p.work_mode = workModeFilter
    }
    return p
  }, [appliedFilter, workModeFilter, page])

  const { data: jobsData, isLoading } = useJobs(params)
  const jobs = jobsData?.jobs || []
  const total = jobsData?.total || 0
  const totalPages = Math.ceil(total / pageSize)
  
  const deleteJob = useDeleteJob()
  const { toast } = useToast()

  const filteredJobs = jobs.filter((job) => {
    const searchLower = searchQuery.toLowerCase()
    return (
      job.job_title?.toLowerCase().includes(searchLower) ||
      job.company_name?.toLowerCase().includes(searchLower) ||
      job.location_text?.toLowerCase().includes(searchLower)
    )
  })

  const handleDelete = async (id: number, title: string) => {
    try {
      await deleteJob.mutateAsync(id)
      toast({
        title: "Job deleted",
        description: `${title} has been deleted.`,
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete job.",
        variant: "destructive",
      })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Job Postings</h1>
          <p className="text-muted-foreground">
            {total > 0 ? `${total} total jobs` : "Manage your ingested job postings"}
          </p>
        </div>
        <div className="flex gap-2">
          <IngestJobsDialog />
          <CreateJobDialog />
        </div>
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
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search jobs..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <Select value={appliedFilter} onValueChange={setAppliedFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Jobs</SelectItem>
                <SelectItem value="applied">Applied</SelectItem>
                <SelectItem value="not-applied">Not Applied</SelectItem>
              </SelectContent>
            </Select>
            <Select value={workModeFilter} onValueChange={setWorkModeFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Work Modes</SelectItem>
                <SelectItem value="remote">Remote</SelectItem>
                <SelectItem value="hybrid">Hybrid</SelectItem>
                <SelectItem value="onsite">On-site</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Jobs List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : filteredJobs && filteredJobs.length > 0 ? (
        <div className="grid gap-4">
          {filteredJobs.map((job) => (
            <Card key={job.id}>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div className="space-y-2 flex-1">
                    <div className="flex items-start gap-3">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold">{job.job_title || "Unknown Position"}</h3>
                        <p className="text-muted-foreground">{job.company_name || "Unknown Company"}</p>
                      </div>
                      <Badge variant={job.has_been_applied_to ? "default" : "outline"}>
                        {job.has_been_applied_to ? "Applied" : "Not Applied"}
                      </Badge>
                    </div>
                    <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
                      {job.location_text && <span>{job.location_text}</span>}
                      {job.work_mode && (
                        <>
                          <span>•</span>
                          <span className="capitalize">{job.work_mode}</span>
                        </>
                      )}
                      {job.employment_type && (
                        <>
                          <span>•</span>
                          <span>{job.employment_type}</span>
                        </>
                      )}
                    </div>
                    {job.skills && job.skills.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {job.skills.map((skill) => (
                          <Badge key={skill} variant="secondary" className="text-xs">
                            {skill}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 ml-4">
                    <Button size="sm" variant="outline" asChild>
                      <a href={job.job_url} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="mr-2 h-4 w-4" />
                        View Job
                      </a>
                    </Button>
                    {!job.has_been_applied_to && (
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button size="sm" variant="destructive">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                            <AlertDialogDescription>
                              This will permanently delete this job posting.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction onClick={() => handleDelete(job.id, job.job_title || "this job")}>
                              Delete
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
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
              <h3 className="mb-2 text-lg font-medium">No jobs found</h3>
              <p className="mb-4 text-sm text-muted-foreground">
                {searchQuery || appliedFilter !== "all" || workModeFilter !== "all"
                  ? "Try adjusting your filters"
                  : "Add your first job posting to get started"}
              </p>
              <CreateJobDialog />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pagination */}
      {jobs.length > 0 && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Showing {page * pageSize + 1} to {Math.min((page + 1) * pageSize, total)} of {total} jobs
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
            >
              Previous
            </Button>
            <div className="flex items-center gap-2 px-3">
              <span className="text-sm">
                Page {page + 1} of {totalPages}
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={page >= totalPages - 1}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
