import { SectionLabel } from "@/components/results/section-label"
import { Progress } from "@/components/ui/progress"
import {
  formatInteger,
  formatPercent,
  ratio,
  type Progress as ProgressData,
} from "@/lib/results"

function CountOf({ part, whole }: { part: number; whole: number }) {
  return (
    <span className="whitespace-nowrap">
      <span className="font-medium text-foreground">{formatInteger(part)}</span>{" "}
      de {formatInteger(whole)}
    </span>
  )
}

export function ProgressPanel({ progress }: { progress: ProgressData }) {
  const electorateRatio = ratio(
    progress.counted_electorate,
    progress.total_electorate
  )

  return (
    <section aria-labelledby="progress-title" className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-1">
        <div id="progress-title">
          <SectionLabel>Seções totalizadas</SectionLabel>
        </div>
        {progress.is_complete && (
          <span className="text-xs font-medium text-muted-foreground">
            Totalização concluída
          </span>
        )}
      </div>
      <p className="text-5xl font-semibold tracking-tight sm:text-6xl">
        {formatPercent(progress.ratio)}
      </p>
      <Progress
        value={progress.ratio * 100}
        aria-label="Seções totalizadas"
        className="h-2 rounded-sm"
      />
      <div className="flex flex-col gap-1 text-sm text-muted-foreground sm:flex-row sm:justify-between sm:gap-4">
        <p>
          <CountOf
            part={progress.counted_sections}
            whole={progress.total_sections}
          />{" "}
          seções
        </p>
        <p>
          Eleitorado apurado:{" "}
          <CountOf
            part={progress.counted_electorate}
            whole={progress.total_electorate}
          />{" "}
          <span className="whitespace-nowrap">
            ({formatPercent(electorateRatio)})
          </span>
        </p>
      </div>
    </section>
  )
}
