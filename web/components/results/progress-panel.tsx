import { SectionLabel } from "@/components/results/section-label"
import { Progress } from "@/components/ui/progress"
import {
  formatInteger,
  formatPercent,
  ratio,
  type Progress as ProgressData,
} from "@/lib/results"

export function ProgressPanel({ progress }: { progress: ProgressData }) {
  const electorateRatio = ratio(
    progress.counted_electorate,
    progress.total_electorate
  )

  return (
    <section aria-labelledby="progress-title" className="space-y-3">
      <div className="flex items-end justify-between gap-4">
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
      <div className="flex flex-col gap-1 text-sm text-muted-foreground sm:flex-row sm:justify-between">
        <p>
          <span className="font-medium text-foreground">
            {formatInteger(progress.counted_sections)}
          </span>{" "}
          de {formatInteger(progress.total_sections)} seções
        </p>
        <p>
          Eleitorado apurado:{" "}
          <span className="font-medium text-foreground">
            {formatInteger(progress.counted_electorate)}
          </span>{" "}
          de {formatInteger(progress.total_electorate)} (
          {formatPercent(electorateRatio)})
        </p>
      </div>
    </section>
  )
}
