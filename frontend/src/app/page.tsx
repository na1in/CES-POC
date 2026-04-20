import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-8">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-xl">CES — Payment Resolution</CardTitle>
            <Badge variant="success">Setup OK</Badge>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-muted-foreground text-sm">
            shadcn/ui + Tailwind v4 initialized. Start building pages.
          </p>
          <div className="flex gap-2">
            <Button size="sm">Analyst Queue</Button>
            <Button size="sm" variant="outline">Governance</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
