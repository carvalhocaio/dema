import { SectionLabel } from "@/components/results/section-label"
import { StateList } from "@/components/results/state-list"
import { StateMap } from "@/components/results/state-map"
import type { Candidate } from "@/lib/results"
import { byRegion, REGION_LABELS, type States } from "@/lib/states"

export function StatesSection({
  states,
  candidates,
  palette,
}: {
  states: States | null
  candidates: readonly Candidate[]
  palette: readonly number[]
}) {
  return (
    <section aria-labelledby="states-title" className="space-y-4">
      <div id="states-title">
        <SectionLabel>Por estado · líder em cada UF</SectionLabel>
      </div>
      {states ? (
        <div className="grid gap-8 lg:grid-cols-12 lg:gap-x-12">
          <div className="mx-auto w-full max-w-md lg:col-span-5">
            <StateMap
              states={states}
              candidates={candidates}
              palette={palette}
            />
            <ul
              aria-label="Regiões"
              className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground"
            >
              {[...byRegion(states.states)].map(([region, items]) => (
                <li key={region}>
                  <span className="font-medium text-foreground">
                    {REGION_LABELS[region]}
                  </span>{" "}
                  {items.map((item) => item.state).join(" ")}
                </li>
              ))}
            </ul>
          </div>
          <div className="lg:col-span-7">
            <StateList
              states={states}
              candidates={candidates}
              palette={palette}
            />
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Aguardando os primeiros boletins.
        </p>
      )}
    </section>
  )
}
