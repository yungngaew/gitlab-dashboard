interface KPICardProps {
  label: string
  value: number
  change?: {
    value: number
    type: 'positive' | 'negative' | 'neutral'
  }
  icon?: React.ReactNode
}

export function KPICard({ label, value, change, icon }: KPICardProps) {
  return (
    <div className="bg-card rounded-lg border p-6 hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start mb-2">
        <span className="text-sm font-medium text-muted-foreground">{label}</span>
        {icon && (
          <div className="text-muted-foreground">
            {icon}
          </div>
        )}
      </div>
      
      <div className="text-3xl font-bold mb-1">
        {value.toLocaleString()}
      </div>

      {change && (
        <div className={`text-sm flex items-center gap-1
          ${change.type === 'positive' ? 'text-green-600' : ''}
          ${change.type === 'negative' ? 'text-red-600' : ''}
          ${change.type === 'neutral' ? 'text-muted-foreground' : ''}
        `}>
          <span>
            {change.type === 'positive' && '↑'}
            {change.type === 'negative' && '↓'}
            {change.type === 'neutral' && '→'}
          </span>
          <span>{Math.abs(change.value)}% from last month</span>
        </div>
      )}
    </div>
  )
} 