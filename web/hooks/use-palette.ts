"use client"

import { useEffect, useState } from "react"

import { apiUrl } from "@/lib/api"
import { palette } from "@/lib/candidate-colors"
import type { Results } from "@/lib/results"

export function usePalette(
  hasFirstRound: boolean,
  results: Results | null
): number[] {
  const [firstRound, setFirstRound] = useState<number[]>([])

  useEffect(() => {
    if (!hasFirstRound) return
    const controller = new AbortController()
    const load = async () => {
      try {
        const response = await fetch(apiUrl("/rounds/1/results"), {
          signal: controller.signal,
          cache: "no-store",
        })
        if (!response.ok) return
        const body = (await response.json()) as Results
        setFirstRound(body.candidates.map((candidate) => candidate.number))
      } catch {
        return
      }
    }
    void load()
    return () => controller.abort()
  }, [hasFirstRound])

  return palette(
    firstRound,
    results?.candidates.map((candidate) => candidate.number) ?? []
  )
}
