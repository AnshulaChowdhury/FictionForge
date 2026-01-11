/**
 * Status Badge Component for Job Status Display (Epic 10)
 * Theme-aware styling.
 */

import { Badge } from '@/components/ui/badge'
import { CheckCircle2, Clock, XCircle, AlertCircle, Ban } from 'lucide-react'

export type JobStatus = 'queued' | 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled'

interface StatusBadgeProps {
  status: JobStatus
  showIcon?: boolean
  className?: string
}

const statusConfig: Record<
  JobStatus,
  {
    variant: 'default' | 'secondary' | 'destructive' | 'outline'
    label: string
    icon: React.ComponentType<{ className?: string }>
    className: string
  }
> = {
  queued: {
    variant: 'secondary',
    label: 'Queued',
    icon: Clock,
    className: 'bg-muted text-muted-foreground border-border',
  },
  pending: {
    variant: 'secondary',
    label: 'Pending',
    icon: Clock,
    className: 'bg-muted text-muted-foreground border-border',
  },
  in_progress: {
    variant: 'default',
    label: 'In Progress',
    icon: AlertCircle,
    className: 'bg-accent/10 text-accent border-accent/30',
  },
  completed: {
    variant: 'outline',
    label: 'Completed',
    icon: CheckCircle2,
    className: 'bg-success/10 text-success border-success/30',
  },
  failed: {
    variant: 'destructive',
    label: 'Failed',
    icon: XCircle,
    className: 'bg-destructive/10 text-destructive border-destructive/30',
  },
  cancelled: {
    variant: 'outline',
    label: 'Cancelled',
    icon: Ban,
    className: 'bg-warning/10 text-warning border-warning/30',
  },
}

export function StatusBadge({ status, showIcon = true, className }: StatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.queued
  const Icon = config.icon

  return (
    <Badge variant={config.variant} className={`${config.className} ${className || ''}`}>
      {showIcon && <Icon className="mr-1 h-3 w-3" />}
      {config.label}
    </Badge>
  )
}
