import { SectionLabel } from "@/components/results/section-label"
import { TimelineChart } from "@/components/results/timeline-chart"
import type { Candidate } from "@/lib/results"
import type { Timeline } from "@/lib/timeline"

export function TimelineSection({
  timeline,
  candidates,
  palette,
}: {
  timeline: Timeline | null
  candidates: readonly Candidate[]
  palette: readonly number[]
}) {
  return (
    <section aria-labelledby="timeline-title" className="space-y-3">
      <div id="timeline-title">
        <SectionLabel>Minuto a minuto · % dos votos válidos</SectionLabel>
      </div>
      {timeline && timeline.points.length > 0 ? (
        <TimelineChart
          timeline={timeline}
          candidates={candidates}
          palette={palette}
        />
      ) : (
        <p className="text-sm text-muted-foreground">
          Aguardando os primeiros boletins.
        </p>
      )}
    </section>
  )
}
