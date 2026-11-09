export function CandidateMarker({ color }: { color: string }) {
  return (
    <span
      aria-hidden
      className="inline-block size-2.5 shrink-0 rounded-[2px]"
      style={{ backgroundColor: color }}
    />
  )
}
