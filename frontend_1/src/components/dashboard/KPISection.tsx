import { KPICard } from './KPICard'

interface KPISectionProps {
  data: {
    totalCommits: number
    commitsChange: number
    mergeRequests: number
    mergeRequestsChange: number
    issuesResolved: number
    issuesResolvedChange: number
    activeProjects: number
    activeProjectsChange: number
  }
}

export function KPISection({ data }: KPISectionProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <KPICard
        label="Total Commits"
        value={data.totalCommits}
        change={{
          value: data.commitsChange,
          type: data.commitsChange >= 0 ? 'positive' : 'negative'
        }}
      />
      <KPICard
        label="Merge Requests"
        value={data.mergeRequests}
        change={{
          value: data.mergeRequestsChange,
          type: data.mergeRequestsChange >= 0 ? 'positive' : 'negative'
        }}
      />
      <KPICard
        label="Issues Resolved"
        value={data.issuesResolved}
        change={{
          value: data.issuesResolvedChange,
          type: data.issuesResolvedChange >= 0 ? 'positive' : 'negative'
        }}
      />
      <KPICard
        label="Active Projects"
        value={data.activeProjects}
        change={{
          value: data.activeProjectsChange,
          type: data.activeProjectsChange >= 0 ? 'positive' : 'negative'
        }}
      />
    </div>
  )
} 