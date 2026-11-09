import { ConnectionIndicator } from "@/components/results/connection-indicator"
import type { ConnectionStatus } from "@/lib/connection"
import { roundLabel } from "@/lib/results"

export function ResultsHeader({
  year,
  round,
  status,
}: {
  year: number
  round: number
  status: ConnectionStatus
}) {
  return (
    <header className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Apuração · Eleição {year}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground sm:text-base">
          Presidente · {roundLabel(round)}
        </p>
      </div>
      <div className="pt-1.5">
        <ConnectionIndicator {...status} />
      </div>
    </header>
  )
}
