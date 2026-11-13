import { ChevronRight } from "lucide-react"

import { formatInteger } from "@/lib/results"
import {
  activeConsumers,
  formatIdle,
  formatRate,
  sparklinePoints,
  type Pipeline,
} from "@/lib/pipeline"
import { cn } from "@/lib/utils"

const SPARK_WIDTH = 240
const SPARK_HEIGHT = 48

export function PipelinePanel({ pipeline }: { pipeline: Pipeline }) {
  const active = activeConsumers(pipeline)
  const points = sparklinePoints(pipeline.rates, SPARK_WIDTH, SPARK_HEIGHT)
  const metrics: Array<[string, string]> = [
    ["Rodada", `#${pipeline.run.id} · seed ${pipeline.run.seed}`],
    ["BUs por segundo", formatRate(pipeline.rate)],
    ["Pico", formatRate(pipeline.peak_rate)],
    ["Seções apuradas", formatInteger(pipeline.counted_sections)],
    ["Mensagens no stream", formatInteger(pipeline.stream_length)],
    ["Pendentes", formatInteger(pipeline.pending)],
    ["Atraso", pipeline.lag === null ? "—" : formatInteger(pipeline.lag)],
    ["Rejeitados", formatInteger(pipeline.rejected)],
  ]

  return (
    <details className="group rounded-lg border bg-card text-card-foreground">
      <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-3 [&::-webkit-details-marker]:hidden">
        <span className="flex items-center gap-2 text-sm font-medium">
          <ChevronRight
            aria-hidden
            className="size-4 text-muted-foreground transition-transform group-open:rotate-90 motion-reduce:transition-none"
          />
          Bastidores
        </span>
        <span className="text-xs text-muted-foreground">
          {formatRate(pipeline.rate)} BUs/s · {active} de{" "}
          {pipeline.consumers.length} workers ativos
        </span>
      </summary>
      <div className="space-y-6 border-t px-4 py-4">
        <div className="grid gap-6 md:grid-cols-12">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-4 md:col-span-8">
            {metrics.map(([label, value]) => (
              <div key={label} className="min-w-0">
                <dt className="text-xs text-muted-foreground">{label}</dt>
                <dd className="truncate font-medium">{value}</dd>
              </div>
            ))}
          </dl>
          <figure className="space-y-1 md:col-span-4">
            <figcaption className="text-xs text-muted-foreground">
              BUs por segundo · último minuto
            </figcaption>
            <svg
              role="img"
              aria-label={`BUs por segundo, ${pipeline.rates.length} amostras, pico de ${formatRate(pipeline.peak_rate)}`}
              viewBox={`0 0 ${SPARK_WIDTH} ${SPARK_HEIGHT}`}
              preserveAspectRatio="none"
              className="h-12 w-full text-foreground"
            >
              <line
                x1={0}
                x2={SPARK_WIDTH}
                y1={SPARK_HEIGHT}
                y2={SPARK_HEIGHT}
                className="stroke-border"
                vectorEffect="non-scaling-stroke"
              />
              {points && (
                <polyline
                  points={points}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1.5}
                  strokeLinejoin="round"
                  vectorEffect="non-scaling-stroke"
                />
              )}
            </svg>
          </figure>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Workers do consumer group</caption>
            <thead className="text-left text-xs text-muted-foreground">
              <tr>
                <th scope="col" className="py-1 pr-4 font-normal">
                  Worker
                </th>
                <th scope="col" className="py-1 pr-4 text-right font-normal">
                  Pendentes
                </th>
                <th scope="col" className="py-1 pr-4 text-right font-normal">
                  Última leitura
                </th>
                <th scope="col" className="py-1 font-normal">
                  Estado
                </th>
              </tr>
            </thead>
            <tbody>
              {pipeline.consumers.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-2 text-muted-foreground">
                    Nenhum worker conectado a esta rodada.
                  </td>
                </tr>
              )}
              {pipeline.consumers.map((consumer) => (
                <tr key={consumer.name} className="border-t">
                  <td className="py-1.5 pr-4 font-mono text-xs">
                    {consumer.name}
                  </td>
                  <td className="py-1.5 pr-4 text-right">
                    {formatInteger(consumer.pending)}
                  </td>
                  <td className="py-1.5 pr-4 text-right">
                    {formatIdle(consumer.idle_ms)}
                  </td>
                  <td className="py-1.5">
                    <span className="inline-flex items-center gap-1.5">
                      <span
                        aria-hidden
                        className={cn(
                          "size-1.5 rounded-full",
                          consumer.active
                            ? "bg-emerald-600 dark:bg-emerald-500"
                            : "bg-muted-foreground/60"
                        )}
                      />
                      {consumer.active ? "Ativo" : "Parado"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </details>
  )
}
