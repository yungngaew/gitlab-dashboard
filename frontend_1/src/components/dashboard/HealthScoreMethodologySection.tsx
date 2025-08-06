'use client'

import { useState } from 'react'

type Tab = 'scoring' | 'grading' | 'example'

const ScoringContent = () => (
  <div>
    <h4 className="font-semibold text-lg mb-2">Health Score Components</h4>
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
      {/* Activity */}
      <div className="bg-muted rounded-lg p-5 shadow-sm">
        <div className="font-bold text-lg mb-2">Activity <span className="text-base font-semibold">(40%)</span></div>
        <ul className="list-disc pl-5 space-y-1 text-sm">
          <li>Commits in last 30 days (0-50+ commits)</li>
          <li>Days since last commit (0-30+ days)</li>
          <li>Contributor diversity (1-10+ contributors)</li>
        </ul>
      </div>
      {/* Maintenance */}
      <div className="bg-muted rounded-lg p-5 shadow-sm">
        <div className="font-bold text-lg mb-2">Maintenance <span className="text-base font-semibold">(30%)</span></div>
        <ul className="list-disc pl-5 space-y-1 text-sm">
          <li>Open issues count (0-20+ issues)</li>
          <li>Issue resolution rate</li>
          <li>Average issue age</li>
        </ul>
      </div>
      {/* Collaboration */}
      <div className="bg-muted rounded-lg p-5 shadow-sm">
        <div className="font-bold text-lg mb-2">Collaboration <span className="text-base font-semibold">(20%)</span></div>
        <ul className="list-disc pl-5 space-y-1 text-sm">
          <li>Merge request activity</li>
          <li>Code review participation</li>
          <li>Branch management practices</li>
        </ul>
      </div>
      {/* Quality */}
      <div className="bg-muted rounded-lg p-5 shadow-sm">
        <div className="font-bold text-lg mb-2">Quality <span className="text-base font-semibold">(10%)</span></div>
        <ul className="list-disc pl-5 space-y-1 text-sm">
          <li>CI/CD pipeline success rate</li>
          <li>Test coverage (if available)</li>
          <li>Documentation completeness</li>
        </ul>
      </div>
    </div>
  </div>
);

const GradingContent = () => (
  <div>
    <h4 className="font-semibold text-lg mb-2">Grading Scale</h4>
    <p className="text-muted-foreground mb-4">The final composite score is mapped to a letter grade to provide a quick, at-a-glance assessment of team health.</p>
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
      <div className="p-4 bg-green-100 dark:bg-green-900/50 rounded-lg">
        <div className="text-2xl font-bold text-green-600 dark:text-green-400">A+</div>
        <div className="text-sm text-muted-foreground">95-100</div>
      </div>
      <div className="p-4 bg-green-100 dark:bg-green-900/50 rounded-lg">
        <div className="text-2xl font-bold text-green-600 dark:text-green-400">A</div>
        <div className="text-sm text-muted-foreground">90-94</div>
      </div>
      <div className="p-4 bg-yellow-100 dark:bg-yellow-900/50 rounded-lg">
        <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">B</div>
        <div className="text-sm text-muted-foreground">80-89</div>
      </div>
      <div className="p-4 bg-orange-100 dark:bg-orange-900/50 rounded-lg">
        <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">C</div>
        <div className="text-sm text-muted-foreground">70-79</div>
      </div>
      <div className="p-4 bg-red-100 dark:bg-red-900/50 rounded-lg">
        <div className="text-2xl font-bold text-red-600 dark:text-red-400">D/F</div>
        <div className="text-sm text-muted-foreground">&lt; 70</div>
      </div>
    </div>
  </div>
);

const ExampleContent = () => (
  <div>
    <h4 className="font-semibold text-lg mb-2">Example Calculation: Frontend Team</h4>
    <p className="text-muted-foreground mb-4">Here's how the "Frontend Team" score (Grade A+) might be calculated:</p>
    <div className="space-y-4">
      <div className="p-3 bg-muted rounded-md">
        <div className="flex justify-between items-center">
          <p><span className="font-medium">1. Commit Frequency:</span> 98 (score)</p>
          <p>98 * 0.30 = <span className="font-bold">29.4</span></p>
        </div>
      </div>
      <div className="p-3 bg-muted rounded-md">
        <div className="flex justify-between items-center">
          <p><span className="font-medium">2. MR Velocity:</span> 95 (score)</p>
          <p>95 * 0.25 = <span className="font-bold">23.75</span></p>
        </div>
      </div>
      <div className="p-3 bg-muted rounded-md">
        <div className="flex justify-between items-center">
          <p><span className="font-medium">3. Issue Resolution:</span> 92 (score)</p>
          <p>92 * 0.20 = <span className="font-bold">18.4</span></p>
        </div>
      </div>
      <div className="p-3 bg-muted rounded-md">
        <div className="flex justify-between items-center">
          <p><span className="font-medium">4. Pipeline Success:</span> 99 (score)</p>
          <p>99 * 0.15 = <span className="font-bold">14.85</span></p>
        </div>
      </div>
      <div className="p-3 bg-muted rounded-md">
        <div className="flex justify-between items-center">
          <p><span className="font-medium">5. Review Engagement:</span> 96 (score)</p>
          <p>96 * 0.10 = <span className="font-bold">9.6</span></p>
        </div>
      </div>
      <div className="mt-4 p-4 border-t-2">
        <div className="flex justify-between items-center text-lg font-bold">
          <span>Total Score:</span>
          <span>29.4 + 23.75 + 18.4 + 14.85 + 9.6 = <span className="text-primary">96.0</span></span>
        </div>
        <div className="flex justify-between items-center text-xl font-bold text-green-500 mt-2">
          <span>Final Grade:</span>
          <span>A+</span>
        </div>
      </div>
    </div>
  </div>
);

export function HealthScoreMethodologySection() {
  const [activeTab, setActiveTab] = useState<Tab>('scoring')

  const renderContent = () => {
    switch (activeTab) {
      case 'scoring':
        return <ScoringContent />
      case 'grading':
        return <GradingContent />
      case 'example':
        return <ExampleContent />
      default:
        return null
    }
  }

  const tabButtonClasses = (tab: Tab) => `
    px-4 py-2 text-sm font-medium rounded-md transition-colors
    ${activeTab === tab 
      ? 'bg-primary text-primary-foreground' 
      : 'text-muted-foreground hover:bg-muted/80 hover:text-foreground'
    }
  `

  return (
    <div className="bg-card text-card-foreground p-6 rounded-lg shadow-sm">
      <h3 className="text-xl font-semibold mb-4">Health Score Methodology</h3>
      <div className="flex space-x-2 mb-4 border-b pb-2">
        <button className={tabButtonClasses('scoring')} onClick={() => setActiveTab('scoring')}>
          Scoring Components
        </button>
        <button className={tabButtonClasses('grading')} onClick={() => setActiveTab('grading')}>
          Grading Scale
        </button>
        <button className={tabButtonClasses('example')} onClick={() => setActiveTab('example')}>
          Calculation Example
        </button>
      </div>
      <div className="mt-4">
        {renderContent()}
      </div>
    </div>
  )
} 