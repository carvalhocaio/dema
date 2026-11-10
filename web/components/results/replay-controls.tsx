import { Pause, Play, Square } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import type {
  ReplayControls as Controls,
  ReplayState,
} from "@/hooks/use-replay"
import { REPLAY_SPEEDS, type ReplaySpeed } from "@/lib/replay"

export function ReplayControls({
  state,
  controls,
  loading,
}: {
  state: ReplayState
  controls: Controls
  loading: boolean
}) {
  if (state.status === "idle") {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={controls.start}
        disabled={loading}
      >
        <Play aria-hidden /> {loading ? "Carregando…" : "Rever apuração"}
      </Button>
    )
  }
  const playing = state.status === "playing"
  return (
    <div
      role="group"
      aria-label="Controles do replay"
      className="flex flex-wrap items-center gap-3"
    >
      <Button
        variant="outline"
        size="icon-sm"
        aria-label={playing ? "Pausar" : "Continuar"}
        onClick={playing ? controls.pause : controls.resume}
      >
        {playing ? <Pause aria-hidden /> : <Play aria-hidden />}
      </Button>
      <Slider
        aria-label="Posição do replay"
        className="w-40 sm:w-56"
        min={0}
        max={1}
        step={0.001}
        value={[state.fraction]}
        onValueChange={([fraction]) => controls.seek(fraction)}
      />
      <ToggleGroup
        type="single"
        variant="outline"
        size="sm"
        aria-label="Velocidade"
        value={String(state.speed)}
        onValueChange={(value) => {
          if (value) controls.setSpeed(Number(value) as ReplaySpeed)
        }}
      >
        {REPLAY_SPEEDS.map((speed) => (
          <ToggleGroupItem key={speed} value={String(speed)}>
            {speed}×
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
      <Button variant="ghost" size="sm" onClick={controls.stop}>
        <Square aria-hidden /> Sair
      </Button>
    </div>
  )
}
