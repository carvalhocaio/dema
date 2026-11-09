import type { Results } from "@/lib/results"

type Listener = (event: MessageEvent<string>) => void

export class FakeEventSource {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSED = 2
  static instances: FakeEventSource[] = []

  readonly url: string
  readyState: number = FakeEventSource.CONNECTING
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  private readonly listeners = new Map<string, Listener>()

  constructor(url: string) {
    this.url = url
    FakeEventSource.instances.push(this)
  }

  static latest(): FakeEventSource {
    const source = FakeEventSource.instances.at(-1)
    if (!source) throw new Error("no EventSource was created")
    return source
  }

  addEventListener(type: string, listener: Listener): void {
    this.listeners.set(type, listener)
  }

  close(): void {
    this.readyState = FakeEventSource.CLOSED
  }

  open(): void {
    this.readyState = FakeEventSource.OPEN
    this.onopen?.()
  }

  emit(results: Results): void {
    const event = new MessageEvent("results", { data: JSON.stringify(results) })
    this.listeners.get("results")?.(event)
  }

  fail(readyState: number): void {
    this.readyState = readyState
    this.onerror?.()
  }
}
