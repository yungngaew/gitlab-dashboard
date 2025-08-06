interface HeaderProps {
  title: string
  subtitle: string
  meta: {
    generatedAt: string
    projectCount: number | undefined
  }
}

export function Header({ title, subtitle, meta }: HeaderProps) {
  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-6 py-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
            <p className="text-muted-foreground">{subtitle}</p>
          </div>
          
          <div className="flex flex-col sm:items-end gap-2 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <span>Generated:</span>
              <span className="font-mono">{meta.generatedAt}</span>
            </div>
            {meta.projectCount !== undefined && (
              <div className="flex items-center gap-2">
                <span>Projects:</span>
                <span className="font-mono">{meta.projectCount}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
} 