"use client"

import { Play } from "lucide-react"
import { useState, type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { parseSeed, requestRun, RunRequestError, type Run } from "@/lib/runs"

export function NewCountDialog({
  onStarted,
}: {
  onStarted: (run: Run) => void
}) {
  const [open, setOpen] = useState(false)
  const [seed, setSeed] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSending(true)
    setError(null)
    try {
      const run = await requestRun(parseSeed(seed))
      setOpen(false)
      setSeed("")
      onStarted(run)
    } catch (failure) {
      setError(
        failure instanceof RunRequestError
          ? failure.message
          : "Não foi possível iniciar a apuração."
      )
    } finally {
      setSending(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Play aria-hidden /> Nova apuração
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={(event) => void submit(event)} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Iniciar uma nova apuração?</DialogTitle>
            <DialogDescription>
              A apuração em andamento será interrompida e uma nova eleição será
              sorteada. Informe uma seed para reproduzir uma eleição anterior.
            </DialogDescription>
          </DialogHeader>
          <label className="block space-y-1.5 text-sm">
            <span className="font-medium">Seed (opcional)</span>
            <Input
              inputMode="numeric"
              placeholder="sorteada se vazia"
              value={seed}
              onChange={(event) => setSeed(event.target.value)}
            />
          </label>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Cancelar
              </Button>
            </DialogClose>
            <Button type="submit" disabled={sending}>
              {sending ? "Iniciando…" : "Iniciar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
