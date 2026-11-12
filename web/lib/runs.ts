import { apiUrl } from "@/lib/api"

export type RunStatus = "preparing" | "counting" | "complete" | "superseded"

export type RunRef = { id: number; round: number; seed: number }

export type Run = RunRef & { status: RunStatus }

export type CurrentRun = { run: Run | null; runs_enabled: boolean }

export class RunRequestError extends Error {}

export function parseSeed(value: string): number | null {
  const trimmed = value.trim()
  if (trimmed === "") return null
  const seed = Number(trimmed)
  if (!Number.isSafeInteger(seed) || seed < 0) {
    throw new RunRequestError("A seed deve ser um número inteiro não negativo.")
  }
  return seed
}

export async function requestRun(seed: number | null): Promise<Run> {
  const response = await fetch(apiUrl("/runs"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(seed === null ? {} : { seed }),
  })
  if (!response.ok) {
    throw new RunRequestError("Não foi possível iniciar a apuração.")
  }
  return (await response.json()) as Run
}
