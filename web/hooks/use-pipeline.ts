"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import { apiUrl } from "@/lib/api"
import type { Pipeline } from "@/lib/pipeline"

export const PIPELINE_POLL_MS = 2_000

export type PipelineState = {
  pipeline: Pipeline | null
  receive: (pipeline: Pipeline) => void
}

/**
 * Follows the pipeline metrics. The live stream pushes them through
 * `receive`; while it is silent (a finished round is on screen, or the
 * stream is down) the hook polls `GET /pipeline` instead.
 */
export function usePipeline(): PipelineState {
  const [pipeline, setPipeline] = useState<Pipeline | null>(null)
  const lastPush = useRef(-Infinity)
  const receive = useCallback((next: Pipeline) => {
    lastPush.current = Date.now()
    setPipeline(next)
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    const load = async () => {
      try {
        const response = await fetch(apiUrl("/pipeline"), {
          signal: controller.signal,
          cache: "no-store",
        })
        if (response.ok) setPipeline((await response.json()) as Pipeline)
      } catch {
        return
      }
    }
    void load()
    const timer = setInterval(() => {
      if (Date.now() - lastPush.current > PIPELINE_POLL_MS) void load()
    }, PIPELINE_POLL_MS)
    return () => {
      clearInterval(timer)
      controller.abort()
    }
  }, [])

  return { pipeline, receive }
}
