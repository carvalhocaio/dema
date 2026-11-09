import { roundLabel } from "@/lib/results"

export function ResultsHeader({
  year,
  round,
}: {
  year: number
  round: number
}) {
  return (
    <header className="space-y-1">
      <h1 className="text-2xl font-semibold tracking-tight text-balance sm:text-3xl">
        Apuração · Eleição {year}
      </h1>
      <p className="text-sm text-muted-foreground sm:text-base">
        Presidente · {roundLabel(round)}
      </p>
    </header>
  )
}
