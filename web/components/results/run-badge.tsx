"use client"

import { Check, Copy } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import type { Run } from "@/lib/runs"

export function RunBadge({ run }: { run: Run }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    await navigator.clipboard.writeText(String(run.seed))
    setCopied(true)
  }

  return (
    <div className="flex items-center gap-1 text-xs text-muted-foreground tabular-nums">
      <span>
        Rodada #{run.id} · seed <span className="font-mono">{run.seed}</span>
      </span>
      <Button
        variant="ghost"
        size="icon-xs"
        aria-label={copied ? "Seed copiada" : "Copiar seed"}
        title={copied ? "Seed copiada" : "Copiar seed"}
        onClick={() => void copy()}
      >
        {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
      </Button>
    </div>
  )
}
