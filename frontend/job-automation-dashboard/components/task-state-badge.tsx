import { Badge } from "@/components/ui/badge"
import { Check, Clock, AlertTriangle, UserCheck, XCircle, Timer, Loader2 } from "lucide-react"
import type { TaskState } from "@/lib/api"

interface TaskStateBadgeProps {
  state: TaskState
  className?: string
}

export function TaskStateBadge({ state, className }: TaskStateBadgeProps) {
  const config = getStateConfig(state)
  const Icon = config.icon

  return (
    <Badge variant={config.variant} className={className}>
      <Icon className="mr-1 h-3 w-3" />
      {config.label}
    </Badge>
  )
}

function getStateConfig(state: TaskState) {
  const configs: Record<TaskState, { label: string; variant: any; icon: any }> = {
    QUEUED: {
      label: "Queued",
      variant: "default",
      icon: Clock,
    },
    RUNNING: {
      label: "Running",
      variant: "secondary",
      icon: Loader2,
    },
    NEEDS_AUTH: {
      label: "Auth Required",
      variant: "destructive",
      icon: AlertTriangle,
    },
    NEEDS_USER: {
      label: "Input Needed",
      variant: "destructive",
      icon: AlertTriangle,
    },
    PENDING_APPROVAL: {
      label: "Review",
      variant: "default",
      icon: UserCheck,
    },
    APPROVED: {
      label: "Approved",
      variant: "default",
      icon: Check,
    },
    SUBMITTED: {
      label: "Submitted",
      variant: "default",
      icon: Check,
    },
    FAILED: {
      label: "Failed",
      variant: "destructive",
      icon: XCircle,
    },
    EXPIRED: {
      label: "Expired",
      variant: "outline",
      icon: Timer,
    },
    REJECTED: {
      label: "Rejected",
      variant: "outline",
      icon: XCircle,
    },
  }

  return configs[state]
}
