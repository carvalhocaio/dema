"use client"

import { useEffect, useState } from "react"

import { apiUrl } from "@/lib/api"
import type { Rejection } from "@/lib/audit"

/** Loads the round's latest rejections again whenever `revision` changes. */
export function useRejected(
  round: number,
  revision: number | null
): Rejection[] | null {
  const [rejections, setRejections] = useState<Rejection[] | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    const load = async () => {
      try {
        const response = await fetch(apiUrl(`/rounds/${round}/rejected`), {
          signal: controller.signal,
          cache: "no-store",
        })
        if (response.ok) setRejections((await response.json()) as Rejection[])
      } catch {
        return
      }
    }
    void load()
    return () => controller.abort()
  }, [round, revision])

  return rejections
}
