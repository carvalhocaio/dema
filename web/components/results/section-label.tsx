export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
      {children}
    </h2>
  )
}
