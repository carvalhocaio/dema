import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export function SetupPendingCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Eleição ainda não preparada</CardTitle>
        <CardDescription>
          A API está no ar, mas nenhuma eleição foi configurada. Prepare o
          catálogo de seções para começar a apuração; a tela atualiza sozinha.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <pre className="rounded-md bg-muted px-3 py-2 font-mono text-xs break-all whitespace-pre-wrap sm:text-sm">
          <code>uv run dema election setup &lt;catalog&gt;</code>
        </pre>
      </CardContent>
    </Card>
  )
}
