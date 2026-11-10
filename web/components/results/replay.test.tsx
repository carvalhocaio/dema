import { act, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ReplayControls } from "@/components/results/replay-controls"
import { RoundView } from "@/components/results/round-view"
import type {
  ReplayClock,
  ReplayControls as Controls,
} from "@/hooks/use-replay"
import { FakeEventSource } from "@/test/event-source"
import { respond, routeFetch } from "@/test/fetch"
import { makeResults } from "@/test/fixtures"
import { renderWithProviders } from "@/test/render"
import { makeReplay } from "@/test/replay"
import { makeTimeline } from "@/test/timeline"

const noop = () => {}
const bigPercent = () => document.querySelector("p.text-5xl")?.textContent
const CONTROLS: Controls = {
  start: vi.fn(),
  pause: vi.fn(),
  resume: vi.fn(),
  stop: vi.fn(),
  seek: vi.fn(),
  setSpeed: vi.fn(),
}

function manualClock() {
  let now = 0
  const ticks = new Set<() => void>()
  const clock: ReplayClock = {
    now: () => now,
    schedule: (tick) => {
      ticks.add(tick)
      return () => ticks.delete(tick)
    },
  }
  return {
    clock,
    advance(ms: number) {
      now += ms
      ticks.forEach((tick) => tick())
    },
  }
}

const FINAL = makeResults({
  verdict: "runoff",
  finalists: [27, 99],
  progress: { ...makeResults().progress, ratio: 1, is_complete: true },
})

function renderFinishedRound(clock: ReplayClock) {
  routeFetch({
    "/rounds/1/results": () => respond(200, FINAL),
    "/rounds/1/timeline": () => respond(200, makeTimeline()),
    "/rounds/1/replay": () => respond(200, makeReplay()),
  })
  const onReport = vi.fn()
  renderWithProviders(
    <RoundView
      round={{ round: 1, status: "live" }}
      hasFirstRound
      onReport={onReport}
      replayClock={clock}
    />
  )
  return onReport
}

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal("EventSource", FakeEventSource)
  vi.clearAllMocks()
})

describe("ReplayControls", () => {
  it("offers to replay while idle and disables it while loading", async () => {
    const { rerender } = renderWithProviders(
      <ReplayControls
        state={{ status: "idle", fraction: 0, speed: 1 }}
        controls={CONTROLS}
        loading={false}
      />
    )
    await userEvent.click(
      screen.getByRole("button", { name: "Rever apuração" })
    )
    expect(CONTROLS.start).toHaveBeenCalled()

    rerender(
      <ReplayControls
        state={{ status: "idle", fraction: 0, speed: 1 }}
        controls={CONTROLS}
        loading
      />
    )
    expect(screen.getByRole("button", { name: "Carregando…" })).toBeDisabled()
  })

  it("pauses, resumes, changes speed, seeks and leaves", async () => {
    const { rerender } = renderWithProviders(
      <ReplayControls
        state={{ status: "playing", fraction: 0.2, speed: 1 }}
        controls={CONTROLS}
        loading={false}
      />
    )
    await userEvent.click(screen.getByRole("button", { name: "Pausar" }))
    expect(CONTROLS.pause).toHaveBeenCalled()

    await userEvent.click(screen.getByRole("radio", { name: "4×" }))
    expect(CONTROLS.setSpeed).toHaveBeenCalledWith(4)
    await userEvent.click(screen.getByRole("radio", { name: "1×" }))
    expect(CONTROLS.setSpeed).toHaveBeenCalledTimes(1)

    const slider = screen.getByRole("slider")
    slider.focus()
    await userEvent.keyboard("{ArrowRight}")
    expect(CONTROLS.seek).toHaveBeenCalledWith(expect.closeTo(0.201, 3))

    await userEvent.click(screen.getByRole("button", { name: "Sair" }))
    expect(CONTROLS.stop).toHaveBeenCalled()

    rerender(
      <ReplayControls
        state={{ status: "paused", fraction: 0.2, speed: 1 }}
        controls={CONTROLS}
        loading={false}
      />
    )
    await userEvent.click(screen.getByRole("button", { name: "Continuar" }))
    expect(CONTROLS.resume).toHaveBeenCalled()
  })

  it("is hidden for an unfinished round", async () => {
    routeFetch({ "/rounds/1/results": () => respond(200, makeResults()) })
    renderWithProviders(
      <RoundView
        round={{ round: 1, status: "live" }}
        hasFirstRound
        onReport={noop}
      />
    )

    expect(await screen.findByText("Seções totalizadas")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Rever apuração" })).toBeNull()
  })
})

describe("RoundView replay", () => {
  it("replays the count from the first minute and ignores live events", async () => {
    const control = manualClock()
    const onReport = renderFinishedRound(control.clock)
    await userEvent.click(
      await screen.findByRole("button", { name: "Rever apuração" })
    )

    await waitFor(() => expect(bigPercent()).toBe("10,00%"))
    expect(onReport).toHaveBeenLastCalledWith({
      label: "Replay",
      tone: "warning",
      year: 2026,
    })
    expect(screen.queryByText("2º turno: Keons × Nico")).toBeNull()

    act(() => FakeEventSource.latest().emit({ ...FINAL, year: 2030 }))
    expect(screen.queryByText("Apuração · Eleição 2030")).toBeNull()
    expect(onReport).toHaveBeenLastCalledWith(
      expect.objectContaining({ year: 2026 })
    )

    act(() => control.advance(20_000))
    expect(bigPercent()).toBe("60,00%")
    expect(screen.queryByText("2º turno: Keons × Nico")).toBeNull()

    act(() => control.advance(30_000))
    expect(bigPercent()).toBe("100,00%")
    expect(screen.getByText("2º turno: Keons × Nico")).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: "Continuar" })
    ).toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: "Sair" }))
    expect(
      screen.getByRole("button", { name: "Rever apuração" })
    ).toBeInTheDocument()
    expect(onReport).toHaveBeenLastCalledWith(
      expect.objectContaining({ label: "Ao vivo" })
    )
  })

  it("keeps the live board while the replay data loads", async () => {
    const control = manualClock()
    routeFetch({
      "/rounds/1/results": () => respond(200, FINAL),
      "/rounds/1/replay": () => new Error("offline"),
    })
    renderWithProviders(
      <RoundView
        round={{ round: 1, status: "final" }}
        hasFirstRound
        onReport={noop}
        replayClock={control.clock}
      />
    )
    await userEvent.click(
      await screen.findByRole("button", { name: "Rever apuração" })
    )

    const group = await screen.findByRole("group", {
      name: "Controles do replay",
    })
    expect(
      within(group).getByRole("button", { name: "Pausar" })
    ).toBeInTheDocument()
    expect(screen.getByText("100,00%")).toBeInTheDocument()
  })
})
