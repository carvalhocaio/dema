const DEFAULT_API_URL = "http://127.0.0.1:8000"

export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL
).replace(/\/+$/, "")

export function apiUrl(path: string): string {
  return `${API_URL}${path}`
}
