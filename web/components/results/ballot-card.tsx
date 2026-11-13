import { ShieldCheck, ShieldQuestion, ShieldX } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { formatClock, type BallotAudit } from "@/lib/audit"
import { formatInteger } from "@/lib/results"

function SignatureSeal({ verified }: { verified: boolean | null }) {
  if (verified === null) {
    return (
      <Badge variant="outline" className="text-muted-foreground">
        <ShieldQuestion aria-hidden /> Assinatura não conferida
      </Badge>
    )
  }
  if (!verified) {
    return (
      <Badge variant="destructive">
        <ShieldX aria-hidden /> Assinatura inválida
      </Badge>
    )
  }
  return (
    <Badge
      variant="outline"
      className="border-emerald-600/40 text-emerald-700 dark:border-emerald-500/40 dark:text-emerald-400"
    >
      <ShieldCheck aria-hidden /> Assinatura válida
    </Badge>
  )
}

export function BallotCard({ ballot }: { ballot: BallotAudit }) {
  const details: Array<[string, string]> = [
    ["Emitido às", formatClock(ballot.issued_at)],
    ["Recebido às", formatClock(ballot.received_at)],
    ["Eleitores aptos", formatInteger(ballot.eligible_voters)],
  ]
  const rows: Array<[string, number]> = [
    ...ballot.candidates.map((candidate): [string, number] => [
      `${candidate.number} · ${candidate.name}`,
      candidate.votes,
    ]),
    ["Brancos", ballot.blank],
    ["Nulos", ballot.null],
  ]

  return (
    <article
      aria-label={`Boletim da seção ${ballot.section}`}
      className="space-y-4 rounded-lg border p-4"
    >
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-mono text-sm font-medium">{ballot.section}</h3>
        <SignatureSeal verified={ballot.verified} />
      </header>
      <dl className="grid grid-cols-3 gap-3 text-sm">
        {details.map(([label, value]) => (
          <div key={label} className="min-w-0">
            <dt className="text-xs text-muted-foreground">{label}</dt>
            <dd className="font-medium">{value}</dd>
          </div>
        ))}
      </dl>
      <table className="w-full text-sm">
        <caption className="sr-only">Votos do boletim</caption>
        <tbody>
          {rows.map(([label, votes]) => (
            <tr key={label} className="border-t first:border-t-0">
              <th scope="row" className="py-1.5 pr-4 text-left font-normal">
                {label}
              </th>
              <td className="py-1.5 text-right font-medium">
                {formatInteger(votes)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="space-y-1">
        <p className="text-xs text-muted-foreground">
          Assinatura (HMAC-SHA3-256)
        </p>
        <p className="font-mono text-xs break-all text-muted-foreground">
          {ballot.signature}
        </p>
      </div>
    </article>
  )
}
