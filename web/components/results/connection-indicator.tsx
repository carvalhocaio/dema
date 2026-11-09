import type { ConnectionStatus, StatusTone } from "@/lib/connection"
import { cn } from "@/lib/utils"

const DOT_CLASS: Record<StatusTone, string> = {
  live: "bg-emerald-600 dark:bg-emerald-500",
  warning: "bg-amber-500",
  idle: "bg-muted-foreground/60",
}

export function ConnectionIndicator({
  label,
  tone,
  className,
}: ConnectionStatus & { className?: string }) {
  return (
    <span
      role="status"
      aria-live="polite"
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 font-medium whitespace-nowrap text-muted-foreground",
        className
      )}
    >
      <span className="relative flex size-2">
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
            "relative inline-flex size-2 rounded-full",
            DOT_CLASS[tone]
          )}
        />
      </span>
      {label}
    </span>
  )
}
