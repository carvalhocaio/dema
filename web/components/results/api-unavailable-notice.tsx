import { API_URL } from "@/lib/api"

export function ApiUnavailableNotice({ hasData }: { hasData: boolean }) {
  return (
    <p
      role="alert"
      className="rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground"
    >
      Não foi possível conectar à API em{" "}
      <code className="font-mono text-foreground">{API_URL}</code>.{" "}
      {hasData
        ? "Exibindo o último placar recebido; tentando reconectar."
        : "Tentando novamente…"}
    </p>
  )
}
