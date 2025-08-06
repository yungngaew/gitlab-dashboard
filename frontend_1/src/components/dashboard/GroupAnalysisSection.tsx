interface GroupData {
  name: string
  health: string
  projectCount: number
  commitCount: number
  activeUsers: number
}

interface GroupAnalysisSectionProps {
  groups: GroupData[]
}

export function GroupAnalysisSection({ groups }: GroupAnalysisSectionProps) {
  return (
    <div className="bg-card rounded-lg border p-6">
      <h2 className="text-2xl font-semibold mb-6">Group Analysis</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {groups.map((group, index) => (
          <div key={`${group.name}-${index}`} className="bg-background rounded-lg border p-4 hover:shadow-lg transition-shadow">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-semibold">{group.name}</h3>
              <div className={`px-3 py-1 rounded-full text-sm font-medium
                ${group.health === 'A+' ? 'bg-green-100 text-green-800' : ''}
                ${group.health  === 'B' ? 'bg-yellow-100 text-yellow-800' : ''}
                ${group.health  === 'C' ? 'bg-red-100 text-red-800' : ''}
              `}>
                Health: {group.health}
              </div>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Projects</span>
                <span className="font-medium">{group.projectCount}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Commits</span>
                <span className="font-medium">{group.commitCount}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Active Users</span>
                <span className="font-medium">{group.activeUsers}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
} 