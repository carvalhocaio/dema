import { ConnectionIndicator } from "@/components/results/connection-indicator"
import { TabsList, TabsTrigger } from "@/components/ui/tabs"
import type { ConnectionStatus } from "@/lib/connection"
import { roundLabel } from "@/lib/results"
import { findRound, ROUND_NUMBERS, type Round } from "@/lib/rounds"

export function RoundTabs({
  rounds,
  liveStatus,
}: {
  rounds: readonly Round[]
  liveStatus: ConnectionStatus
}) {
  return (
    <TabsList aria-label="Turno">
      {ROUND_NUMBERS.map((number) => {
        const round = findRound(rounds, number)
        return (
          <TabsTrigger
            key={number}
            value={String(number)}
            disabled={!round}
            className="gap-2 px-3"
          >
            {roundLabel(number)}
            {round?.status === "live" && (
              <ConnectionIndicator {...liveStatus} className="text-xs" />
            )}
          </TabsTrigger>
        )
      })}
    </TabsList>
  )
}
