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
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { useCreateRun } from "@/lib/hooks/use-api"
import { useToast } from "@/hooks/use-toast"
import { Plus } from "lucide-react"

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
})

type FormData = z.infer<typeof schema>

export function CreateRunDialog() {
  const [open, setOpen] = useState(false)
  const { toast } = useToast()
  const createRun = useCreateRun()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    try {
      await createRun.mutateAsync(data)
      toast({
        title: "Run created",
        description: `${data.name} has been created successfully.`,
      })
      setOpen(false)
      reset()
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create run. Please try again.",
        variant: "destructive",
      })
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          New Run
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Application Run</DialogTitle>
          <DialogDescription>Create a new batch of job applications to process.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" placeholder="e.g., Tech Companies Q1 2025" {...register("name")} />
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description (optional)</Label>
            <Textarea id="description" placeholder="Add any notes about this run..." {...register("description")} />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createRun.isPending}>
              {createRun.isPending ? "Creating..." : "Create Run"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
