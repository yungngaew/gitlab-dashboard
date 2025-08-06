interface IssueStats {
  totalOpen: number
  criticalHigh: {
    total: number
    critical: number
    high: number
  }
  overdue: number
  projectCount: number
}

interface Recommendation {
  title: string
  description: string
  priority: 'critical' | 'high' | 'medium'
  action: string
  context?: string
  icon?: 'alert' | 'warning' | 'info'
}

interface IssuesAnalysisSectionProps {
  stats: IssueStats
  recommendations: Recommendation[]
}

export function IssuesAnalysisSection({ stats, recommendations }: IssuesAnalysisSectionProps) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold mt-6">Issues Analysis & AI Recommendations</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Open Issues */}
        <div className="bg-card rounded-lg border p-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-4">Total Open Issues</h3>
          <div className="text-4xl font-bold mb-2">{stats.totalOpen}</div>
          <div className="text-sm text-muted-foreground">Across {stats.projectCount} projects</div>
        </div>

        {/* Critical/High Priority */}
        <div className="bg-card rounded-lg border p-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-4">Critical/High Priority</h3>
          <div className="text-4xl font-bold mb-2">{stats.criticalHigh.total}</div>
          <div className="text-sm text-muted-foreground">
            {stats.criticalHigh.critical} critical, {stats.criticalHigh.high} high
          </div>
        </div>

        {/* Overdue Issues */}
        <div className="bg-card rounded-lg border p-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-4">Overdue Issues</h3>
          <div className="text-4xl font-bold mb-2">{stats.overdue}</div>
          <div className="text-sm text-muted-foreground">Need immediate attention</div>
        </div>

        {/* AI Recommendations */}
        <div className="bg-card rounded-lg border p-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-4">AI Recommendations</h3>
          <div className="text-4xl font-bold mb-2">{recommendations.length}</div>
          <div className="text-sm text-muted-foreground">Strategic insights generated</div>
        </div>
      </div>

      {/* Strategic Recommendations */}
      <div className="bg-card rounded-lg border p-6">
        <h3 className="text-lg font-semibold mb-6">Strategic Recommendations</h3>
        <div className="space-y-6">
          {recommendations.map((rec, index) => (
            <div key={`${rec.title}-${index}`} className="space-y-2">
              <div className="flex items-start gap-3">
                <div className="mt-1">
                  {rec.icon === 'alert' && (
                    <span className="text-red-500">⚠️</span>
                  )}
                  {rec.icon === 'warning' && (
                    <span className="text-yellow-500">⚠️</span>
                  )}
                  {rec.icon === 'info' && (
                    <span className="text-blue-500">💡</span>
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold ">{rec.title}</h4>
                    <span className={`
                      px-2 py-1 text-xs font-medium rounded-full
                      ${rec.priority === 'critical' ? 'bg-red-100 text-red-800' : ''}
                      ${rec.priority === 'high' ? 'bg-orange-100 text-orange-800' : ''}
                      ${rec.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' : ''}
                    `}>
                      {rec.priority.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">{rec.description}</p>
                  <div className="mt-2">
                    <strong className="text-sm">Action:</strong>
                    <span className="text-sm ml-1">{rec.action}</span>
                  </div>
                  {rec.context && (
                    <div className="text-sm text-muted-foreground mt-1">
                      {rec.context}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
} 