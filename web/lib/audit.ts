import { apiUrl } from "@/lib/api"

export type BallotVote = { number: number; name: string; votes: number }

export type BallotAudit = {
  section: string
  state: string
  issued_at: string
  received_at: string
  eligible_voters: number
  candidates: BallotVote[]
  blank: number
  null: number
  signature: string
  verified: boolean | null
}

export type Rejection = {
  entry: string
  at: string
  reason: string
  section: string | null
}

export type Tampered = { section: string; source: string }

const SECTION_KEY = /^([a-z]{2})-(\d{1,5})-(\d{1,4})-(\d{1,4})$/i

export function normalizeSectionKey(raw: string): string | null {
  const match = SECTION_KEY.exec(raw.trim())
  if (!match) return null
  const [, state, municipality, zone, section] = match
  return [
    state.toUpperCase(),
    municipality.padStart(5, "0"),
    zone.padStart(4, "0"),
    section.padStart(4, "0"),
  ].join("-")
}

const REASONS: Record<string, string> = {
  "invalid signature": "Assinatura inválida",
  "malformed entry": "Entrada malformada",
}

export function rejectionReason(reason: string): string {
  if (reason in REASONS) return REASONS[reason]
  if (reason.startsWith("invalid payload")) return "Conteúdo ilegível"
  return reason
}

const clockFormat = new Intl.DateTimeFormat("pt-BR", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  timeZone: "America/Sao_Paulo",
})

export function formatClock(iso: string): string {
  return clockFormat.format(new Date(iso))
}

export type Lookup =
  { status: "found"; ballot: BallotAudit } | { status: "missing" | "error" }

export async function fetchBallot(
  round: number,
  section: string | null
): Promise<Lookup> {
  const path = section === null ? "random" : encodeURIComponent(section)
  try {
    const response = await fetch(apiUrl(`/rounds/${round}/sections/${path}`), {
      cache: "no-store",
    })
    if (response.status === 404) return { status: "missing" }
    if (!response.ok) return { status: "error" }
    return { status: "found", ballot: (await response.json()) as BallotAudit }
  } catch {
    return { status: "error" }
  }
}

export type TamperResult =
  { status: "sent"; tampered: Tampered } | { status: "unavailable" | "error" }

export async function requestTamper(round: number): Promise<TamperResult> {
  try {
    const response = await fetch(apiUrl(`/rounds/${round}/tamper`), {
      method: "POST",
    })
    if (response.status === 409) return { status: "unavailable" }
    if (!response.ok) return { status: "error" }
    return { status: "sent", tampered: (await response.json()) as Tampered }
  } catch {
    return { status: "error" }
  }
}
