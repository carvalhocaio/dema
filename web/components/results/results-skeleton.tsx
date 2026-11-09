import { Skeleton } from "@/components/ui/skeleton"

const ROWS = [0, 1, 2, 3, 4]

export function ResultsSkeleton() {
  return (
    <div aria-busy className="space-y-10" aria-label="Carregando resultados">
      <div className="space-y-3">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-14 w-48" />
        <Skeleton className="h-2 w-full" />
        <Skeleton className="h-4 w-56" />
      </div>
      <div className="divide-y border-y">
        {ROWS.map((row) => (
          <div key={row} className="flex items-center gap-4 py-5">
            <Skeleton className="h-10 w-12" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-2.5 w-full" />
            </div>
            <Skeleton className="h-8 w-24" />
          </div>
        ))}
      </div>
    </div>
  )
}
