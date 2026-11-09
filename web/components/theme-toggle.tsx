"use client"

import { Monitor, Moon, Sun, type LucideIcon } from "lucide-react"
import { useTheme } from "next-themes"
import { useSyncExternalStore } from "react"

import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

const THEMES: ReadonlyArray<{
  value: string
  label: string
  Icon: LucideIcon
}> = [
  { value: "system", label: "Tema do sistema", Icon: Monitor },
  { value: "light", label: "Tema claro", Icon: Sun },
  { value: "dark", label: "Tema escuro", Icon: Moon },
]

function subscribe(): () => void {
  return () => {}
}

function onClient(): boolean {
  return true
}

function onServer(): boolean {
  return false
}

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const mounted = useSyncExternalStore(subscribe, onClient, onServer)

  return (
    <ToggleGroup
      type="single"
      variant="outline"
      size="sm"
      aria-label="Tema"
      value={mounted ? theme : ""}
      onValueChange={(value) => {
        if (value) setTheme(value)
      }}
    >
      {THEMES.map(({ value, label, Icon }) => (
        <ToggleGroupItem
          key={value}
          value={value}
          aria-label={label}
          title={label}
        >
          <Icon aria-hidden />
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  )
}
