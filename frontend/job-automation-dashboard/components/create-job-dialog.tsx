"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useCreateJob } from "@/lib/hooks/use-api"
import { useToast } from "@/hooks/use-toast"
import { Plus } from "lucide-react"

const schema = z.object({
  job_url: z.string().url("Must be a valid URL"),
  apply_url: z.string().url("Must be a valid URL"),
  company_name: z.string().optional(),
  job_title: z.string().optional(),
  location_text: z.string().optional(),
  work_mode: z.enum(["remote", "hybrid", "onsite"]).optional(),
})

type FormData = z.infer<typeof schema>

export function CreateJobDialog() {
  const [open, setOpen] = useState(false)
  const { toast } = useToast()
  const createJob = useCreateJob()

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    try {
      await createJob.mutateAsync(data)
      toast({
        title: "Job added",
        description: "The job posting has been added successfully.",
      })
      setOpen(false)
      reset()
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to add job. Please try again.",
        variant: "destructive",
      })
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Add Job
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add Job Posting</DialogTitle>
          <DialogDescription>Add a new job posting to your database for future application runs.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="job_url">Job URL</Label>
            <Input id="job_url" placeholder="https://..." {...register("job_url")} />
            {errors.job_url && <p className="text-sm text-destructive">{errors.job_url.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="apply_url">Apply URL</Label>
            <Input id="apply_url" placeholder="https://..." {...register("apply_url")} />
            {errors.apply_url && <p className="text-sm text-destructive">{errors.apply_url.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="company_name">Company Name (optional)</Label>
            <Input id="company_name" placeholder="e.g., Acme Corp" {...register("company_name")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="job_title">Job Title (optional)</Label>
            <Input id="job_title" placeholder="e.g., Senior Software Engineer" {...register("job_title")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="location_text">Location (optional)</Label>
            <Input id="location_text" placeholder="e.g., San Francisco, CA" {...register("location_text")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="work_mode">Work Mode (optional)</Label>
            <Select onValueChange={(value) => setValue("work_mode", value as any)}>
              <SelectTrigger>
                <SelectValue placeholder="Select work mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="remote">Remote</SelectItem>
                <SelectItem value="hybrid">Hybrid</SelectItem>
                <SelectItem value="onsite">On-site</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createJob.isPending}>
              {createJob.isPending ? "Adding..." : "Add Job"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
