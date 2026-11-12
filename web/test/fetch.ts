import { vi } from "vitest"

import { makeResults } from "@/test/fixtures"

export type FetchResponse = { status: number; ok: boolean; json: () => unknown }

export function respond(status: number, body: unknown = {}): FetchResponse {
  return { status, ok: status >= 200 && status < 300, json: () => body }
}

export function stubFetch(...responses: Array<FetchResponse | Error>) {
  const queue = [...responses]
  const fetchMock = vi.fn<
    (url: string, init?: RequestInit) => Promise<FetchResponse>
  >(async () => {
    const next = queue.shift() ?? respond(200, makeResults())
    if (next instanceof Error) throw next
    return next
  })
  vi.stubGlobal("fetch", fetchMock)
  return fetchMock
}

export function routeFetch(
  routes: Record<string, () => FetchResponse | Error>
) {
  const fetchMock = vi.fn<
    (url: string, init?: RequestInit) => Promise<FetchResponse>
  >(async (url) => {
    const path = new URL(url).pathname
    const route = routes[path]
    const next = route ? route() : respond(404)
    if (next instanceof Error) throw next
    return next
  })
  vi.stubGlobal("fetch", fetchMock)
  return fetchMock
}
