"use client"

import { Dices, Search, ShieldAlert } from "lucide-react"
import { useState, type FormEvent } from "react"

import { BallotCard } from "@/components/results/ballot-card"
import { SectionLabel } from "@/components/results/section-label"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useBallotLookup, type LookupState } from "@/hooks/use-ballot-lookup"
import { useRejected } from "@/hooks/use-rejected"
import {
  formatClock,
  rejectionReason,
  requestTamper,
  type Rejection,
} from "@/lib/audit"

function lookupMessage(state: LookupState): string | null {
  switch (state.status) {
    case "loading":
      return "Consultando…"
    case "invalid":
      return "Chave inválida. Use UF-município-zona-seção, como SP-71072-0001-0042."
    case "missing":
      return state.section === null
        ? "Nenhuma seção foi apurada neste turno ainda."
        : `A seção ${state.section} ainda não foi apurada neste turno.`
    case "error":
      return "Não foi possível consultar o boletim."
    default:
      return null
  }
}

function RejectedList({ rejections }: { rejections: Rejection[] | null }) {
  if (rejections === null) return null
  if (rejections.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Nenhum boletim rejeitado neste turno.
      </p>
    )
  }
  return (
    <ol aria-label="Boletins rejeitados" className="text-sm">
      {rejections.map((rejection) => (
        <li
          key={rejection.entry}
          className="flex flex-wrap items-baseline justify-between gap-x-3 border-t py-1.5 first:border-t-0"
        >
          <span>
            {rejectionReason(rejection.reason)}
            <span className="ml-2 font-mono text-xs text-muted-foreground">
              {rejection.section ?? "seção ilegível"}
            </span>
          </span>
          <span className="text-xs text-muted-foreground">
            {formatClock(rejection.at)}
          </span>
        </li>
      ))}
    </ol>
  )
}

function TamperButton({ round }: { round: number }) {
  const [message, setMessage] = useState<string | null>(null)
  const [sending, setSending] = useState(false)

  const tamper = async () => {
    setSending(true)
    const result = await requestTamper(round)
    setSending(false)
    setMessage(
      result.status === "sent"
        ? `BU adulterado enviado para a seção ${result.tampered.section}, com a assinatura do boletim de ${result.tampered.source}.`
        : result.status === "unavailable"
          ? "Não há seção disponível para adulterar agora."
          : "Não foi possível injetar o BU adulterado."
    )
  }

  return (
    <div className="space-y-2">
      <Button
        variant="outline"
        size="sm"
        disabled={sending}
        onClick={() => void tamper()}
      >
        <ShieldAlert aria-hidden /> Injetar BU adulterado
      </Button>
      {message && (
        <p role="status" className="text-xs text-muted-foreground">
          {message}
        </p>
      )}
    </div>
  )
}

export function AuditSection({
  round,
  canTamper,
  revision,
}: {
  round: number
  canTamper: boolean
  revision: number | null
}) {
  const [query, setQuery] = useState("")
  const { state, search, draw } = useBallotLookup(round)
  const rejections = useRejected(round, revision)
  const message = lookupMessage(state)

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    search(query)
  }

  return (
    <section aria-labelledby="audit-title" className="space-y-4">
      <div id="audit-title">
        <SectionLabel>Auditoria · conferência de boletins</SectionLabel>
      </div>
      <div className="grid gap-8 lg:grid-cols-12 lg:gap-x-12">
        <div className="min-w-0 space-y-4 lg:col-span-7">
          <form
            role="search"
            aria-label="Consultar boletim"
            onSubmit={submit}
            className="flex flex-wrap gap-2"
          >
            <label htmlFor="audit-section-key" className="sr-only">
              Chave da seção
            </label>
            <Input
              id="audit-section-key"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="SP-71072-0001-0042"
              autoComplete="off"
              spellCheck={false}
              className="min-w-0 flex-1 basis-48 font-mono"
            />
            <Button type="submit" size="sm" className="h-9">
              <Search aria-hidden /> Consultar
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-9"
              onClick={draw}
            >
              <Dices aria-hidden /> Seção aleatória
            </Button>
          </form>
          {message && (
            <p role="status" className="text-sm text-muted-foreground">
              {message}
            </p>
          )}
          {state.status === "found" && <BallotCard ballot={state.ballot} />}
        </div>
        <div className="min-w-0 space-y-3 lg:col-span-5">
          <h3 className="text-sm font-medium">Rejeitados</h3>
          {canTamper && <TamperButton round={round} />}
          <RejectedList rejections={rejections} />
        </div>
      </div>
    </section>
  )
}
