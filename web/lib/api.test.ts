import { afterEach, describe, expect, it, vi } from "vitest"

async function loadApi() {
  vi.resetModules()
  return import("@/lib/api")
}

afterEach(() => {
  vi.unstubAllEnvs()
})

describe("apiUrl", () => {
  it("defaults to the local API", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "")
    const { API_URL, apiUrl } = await loadApi()

    expect(API_URL).toBe("http://127.0.0.1:8000")
    expect(apiUrl("/health")).toBe("http://127.0.0.1:8000/health")
  })

  it("uses the configured base without trailing slashes", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://dema.example//")
    const { apiUrl } = await loadApi()

    expect(apiUrl("/results")).toBe("https://dema.example/results")
  })
})
