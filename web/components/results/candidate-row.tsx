import { CandidateMarker } from "@/components/results/candidate-marker"
import { ShareBar } from "@/components/results/share-bar"
import { Badge } from "@/components/ui/badge"
import { formatInteger, formatPercent, type Candidate } from "@/lib/results"
import { cn } from "@/lib/utils"

export function CandidateRow({
  candidate,
  color,
  badge,
  receded,
}: {
  candidate: Candidate
  color: string
  badge: string | null
  receded: boolean
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-[auto_1fr_auto] items-center gap-x-4 gap-y-3 py-5 transition-opacity duration-500",
        receded && "opacity-50"
      )}
    >
      <span className="row-span-2 self-start rounded-md border px-2 py-1 font-mono text-xl font-semibold sm:text-2xl">
        {candidate.number}
      </span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <CandidateMarker color={color} />
          <span className="truncate text-lg font-semibold">
            {candidate.name}
          </span>
          {badge && <Badge>{badge}</Badge>}
        </div>
        <p className="truncate text-sm text-muted-foreground">
          {candidate.party}
        </p>
      </div>
      <div className="text-right">
        <p className="text-2xl font-semibold tracking-tight sm:text-3xl">
          {formatPercent(candidate.share)}
        </p>
        <p className="text-sm text-muted-foreground">
          {formatInteger(candidate.votes)} votos
        </p>
      </div>
      <div className="col-span-2 col-start-2">
        <ShareBar share={candidate.share} color={color} />
      </div>
    </div>
  )
}
