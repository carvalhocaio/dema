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
    <header className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1">
      <h1 className="col-span-2 text-2xl font-semibold tracking-tight text-balance sm:col-span-1 sm:text-3xl">
        Apuração · Eleição {year}
      </h1>
      <p className="col-start-1 row-start-2 text-sm text-muted-foreground sm:text-base">
        Presidente · {roundLabel(round)}
      </p>
      <div className="col-start-2 row-start-2 justify-self-end sm:row-start-1">
        <ConnectionIndicator {...status} />
      </div>
    </header>
  )
}
