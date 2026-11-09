import type { Connection, Setup } from "@/hooks/use-round-results"

export type StatusTone = "live" | "warning" | "idle"

export type ConnectionStatus = {
  label: string
  tone: StatusTone
}

export const LIVE_STATUS: ConnectionStatus = { label: "Ao vivo", tone: "live" }

export function connectionStatus(
  connection: Connection,
  setup: Setup
): ConnectionStatus {
  if (connection === "reconnecting")
    return { label: "Reconectando", tone: "warning" }
  if (connection === "unavailable")
    return { label: "Sem conexão", tone: "idle" }
  if (connection === "connecting") return { label: "Conectando", tone: "idle" }
  if (connection === "final") return { label: "Resultado final", tone: "idle" }
  if (setup === "pending") return { label: "Aguardando setup", tone: "idle" }
  return LIVE_STATUS
}

export type StatusReport = ConnectionStatus & { year: number | null }

export function sameReport(a: StatusReport, b: StatusReport): boolean {
  return a.label === b.label && a.tone === b.tone && a.year === b.year
}
