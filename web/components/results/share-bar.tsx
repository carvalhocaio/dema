export function ShareBar({ share, color }: { share: number; color: string }) {
  const width = `${Math.min(Math.max(share, 0), 1) * 100}%`

  return (
    <div className="relative h-2.5 w-full rounded-sm bg-muted" aria-hidden>
      <div
        className="h-full rounded-sm transition-[width] duration-700 ease-out motion-reduce:transition-none"
        style={{ width, backgroundColor: color }}
      />
      <span className="absolute -inset-y-1 left-1/2 w-px bg-foreground/50" />
    </div>
  )
}
