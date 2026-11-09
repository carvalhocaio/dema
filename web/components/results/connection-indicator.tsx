import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { API_URL } from "@/lib/api"
import type { StatusTone } from "@/lib/connection"
import { cn } from "@/lib/utils"

const DOT_CLASS: Record<StatusTone, string> = {
  live: "bg-emerald-600 dark:bg-emerald-500",
  warning: "bg-amber-500",
  idle: "bg-muted-foreground/60",
}

export function ConnectionIndicator({
  label,
  tone,
}: {
  label: string
  tone: StatusTone
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          role="status"
          aria-live="polite"
          tabIndex={0}
          className="flex shrink-0 items-center gap-2 rounded-sm text-sm font-medium whitespace-nowrap text-muted-foreground"
        >
          <span className="relative flex size-2.5">
            {tone === "live" && (
              <span
                className={cn(
                  "absolute inline-flex size-full animate-ping rounded-full opacity-60",
                  DOT_CLASS.live
                )}
              />
            )}
            <span
              className={cn(
                "relative inline-flex size-2.5 rounded-full",
                DOT_CLASS[tone]
              )}
            />
          </span>
          {label}
        </div>
      </TooltipTrigger>
      <TooltipContent>API: {API_URL}</TooltipContent>
    </Tooltip>
  )
}
