// Types
export interface KPIData {
  totalCommits: number
  commitsChange: number
  mergeRequests: number
  mergeRequestsChange: number
  issuesResolved: number
  issuesResolvedChange: number
  activeProjects: number
  activeProjectsChange: number
}

export interface ActivityData {
  date: string
  count: number
  netCodeChange: number
}

export interface GroupData {
  name: string
  health: string
  projectCount: number
  commitCount: number
  activeUsers: number
}

export interface ProjectData {
  id: number
  name: string
  group: string
  status: 'active' | 'archived' | 'maintenance' | 'inactive'
  grade: 'A+' | 'A' | 'B' | 'C' | 'D/F'
  description: string
  issues: number
  mergeRequests: number
  commits: number
  contributors: number
  lastActivity: string
}

export interface ContributorData {
  id: number
  name: string
  email: string
  commits: number
  issues: number
  mergeRequests: number
  lastActivity: string
  projects: number
  activeProjects: string[]
  workload: {
    openIssues: number
    resolved: number
    mrs: number
  }
  netChange: {
    '7d': { net: number, additions: number, deletions: number },
    '15d': { net: number, additions: number, deletions: number },
    '30d': { net: number, additions: number, deletions: number }
  }
}

export interface IssueData {
  id: number
  title: string
  project: string
  assignee: string
  status: 'open' | 'closed' | 'in_progress'
  priority: 'low' | 'medium' | 'high' | 'critical'
  createdAt: string
  updatedAt: string
}

export interface IssueStats {
  totalOpen: number
  criticalHigh: {
    total: number
    critical: number
    high: number
  }
  overdue: number
  projectCount: number
}

export interface Recommendation {
  title: string
  description: string
  priority: 'critical' | 'high' | 'medium'
  action: string
  context?: string
  icon?: 'alert' | 'warning' | 'info'
}

export interface IssuesAnalysisData {
  stats: IssueStats
  recommendations: Recommendation[]
}

// Mock data
const mockGroups: GroupData[] = [
  {
    name: 'Frontend Team',
    health: 'A+',
    projectCount: 12,
    commitCount: 450,
    activeUsers: 8
  },
  {
    name: 'Backend Team',
    health: 'B',
    projectCount: 15,
    commitCount: 620,
    activeUsers: 10
  },
  {
    name: 'DevOps Team',
    health: 'A+',
    projectCount: 8,
    commitCount: 380,
    activeUsers: 6
  },
  {
    name: 'Mobile Team',
    health: 'C',
    projectCount: 10,
    commitCount: 410,
    activeUsers: 7
  },
  {
    name: 'QA Team',
    health: 'A+',
    projectCount: 3,
    commitCount: 180,
    activeUsers: 4
  }
]

const mockProjects: ProjectData[] = [
  {
    id: 1,
    name: 'User Management System',
    group: 'Backend Team',
    status: 'active',
    grade: 'A',
    description: 'Handles user authentication, authorization, and profile management.',
    issues: 45,
    mergeRequests: 23,
    commits: 156,
    contributors: 8,
    lastActivity: '2024-01-15T16:45:00Z'
  },
  {
    id: 2,
    name: 'Dashboard UI',
    group: 'Frontend Team',
    status: 'archived',
    grade: 'B',
    description: 'Provides the main dashboard interface for analytics and reporting.',
    issues: 32,
    mergeRequests: 18,
    commits: 89,
    contributors: 6,
    lastActivity: '2024-01-15T15:30:00Z'
  },
  {
    id: 3,
    name: 'Mobile App',
    group: 'Mobile Team',
    status: 'active',
    grade: 'A+',
    description: 'Cross-platform mobile application for end users.',
    issues: 12,
    mergeRequests: 7,
    commits: 54,
    contributors: 4,
    lastActivity: '2024-01-14T10:20:00Z'
  },
  {
    id: 4,
    name: 'CI/CD Pipeline',
    group: 'DevOps Team',
    status: 'active',
    grade: 'C',
    description: 'Automates build, test, and deployment processes.',
    issues: 8,
    mergeRequests: 5,
    commits: 33,
    contributors: 3,
    lastActivity: '2024-01-13T09:00:00Z'
  },
  {
    id: 5,
    name: 'Legacy API',
    group: 'Backend Team',
    status: 'maintenance',
    grade: 'C',
    description: 'Legacy API system under maintenance mode.',
    issues: 20,
    mergeRequests: 2,
    commits: 200,
    contributors: 2,
    lastActivity: '2024-01-10T08:00:00Z'
  },
  {
    id: 6,
    name: 'Old Mobile App',
    group: 'Mobile Team',
    status: 'inactive',
    grade: 'D/F',
    description: 'Deprecated mobile app, no longer maintained.',
    issues: 0,
    mergeRequests: 0,
    commits: 120,
    contributors: 1,
    lastActivity: '2023-12-01T12:00:00Z'
  }
]

const mockContributors: ContributorData[] = [
  {
    id: 1,
    name: 'Jedsada Srijunpoe',
    email: 'jedsada@company.com',
    commits: 85,
    issues: 5,
    mergeRequests: 22,
    lastActivity: '2024-01-15T16:30:00Z',
    projects: 8,
    activeProjects: [
      'ai-survey', 'copilot-ai-survey', 'cyber-security-research', 'dts-code-buddy', 'dts-po-buddy', 'dts-study', 'ds-buddy', 'ds-study'
    ],
    workload: {
      openIssues: 5,
      resolved: 17,
      mrs: 22
    },
    netChange: {
      '7d': { net: 19, additions: 72, deletions: 53 },
      '15d': { net: 41, additions: 92, deletions: 51 },
      '30d': { net: -59, additions: 192, deletions: 251 }
    }
  },
  {
    id: 2,
    name: 'Your Name',
    email: 'your.name@company.com',
    commits: 59,
    issues: 0,
    mergeRequests: 0,
    lastActivity: '2024-01-15T14:20:00Z',
    projects: 3,
    activeProjects: [
      'copilot-survey-bot', 'cyber-security-research', 'llama-index-rag-pipeline'
    ],
    workload: {
      openIssues: 0,
      resolved: 0,
      mrs: 0
    },
    netChange: {
      '7d': { net: 0, additions: 0, deletions: 0 },
      '15d': { net: 0, additions: 0, deletions: 0 },
      '30d': { net: 0, additions: 0, deletions: 0 }
    }
  },
  {
    id: 3,
    name: 'Totrakool Khongsap',
    email: 'totrakool@company.com',
    commits: 58,
    issues: 0,
    mergeRequests: 9,
    lastActivity: '2024-01-15T13:00:00Z',
    projects: 8,
    activeProjects: [
      'Cybersecuity Log Frontend', 'azure-ocr-pipeline', 'cyber-security-research', 'e-recruitment-suite', 'issues-generator-automation', 'copilot-ai-survey', 'ai-survey', 'dts-study'
    ],
    workload: {
      openIssues: 0,
      resolved: 1,
      mrs: 9
    },
    netChange: {
      '7d': { net: 19, additions: 72, deletions: 53 },
      '15d': { net: 41, additions: 92, deletions: 51 },
      '30d': { net: -59, additions: 192, deletions: 251 }
    }
  },
  {
    id: 4,
    name: 'tkhongsap',
    email: 'tkhongsap@company.com',
    commits: 50,
    issues: 0,
    mergeRequests: 0,
    lastActivity: '2024-01-14T10:00:00Z',
    projects: 4,
    activeProjects: [
      'Cybersecuity Log Frontend', 'copilot-survey-bot', 'landsmap-thailand', 'llama-index-rag-pipeline'
    ],
    workload: {
      openIssues: 0,
      resolved: 0,
      mrs: 0
    },
    netChange: {
      '7d': { net: 0, additions: 0, deletions: 0 },
      '15d': { net: 0, additions: 0, deletions: 0 },
      '30d': { net: 0, additions: 0, deletions: 0 }
    }
  }
]

const mockIssues: IssueData[] = [
  {
    id: 1,
    title: 'Fix authentication bug in login flow',
    project: 'User Management System',
    assignee: 'John Doe',
    status: 'in_progress',
    priority: 'high',
    createdAt: '2024-01-10T09:00:00Z',
    updatedAt: '2024-01-15T14:30:00Z'
  },
  {
    id: 2,
    title: 'Add dark mode support',
    project: 'Dashboard UI',
    assignee: 'Jane Smith',
    status: 'open',
    priority: 'medium',
    createdAt: '2024-01-12T11:00:00Z',
    updatedAt: '2024-01-12T11:00:00Z'
  }
]

const mockKPIData: KPIData = {
  totalCommits: 1248,
  commitsChange: 15,
  mergeRequests: 186,
  mergeRequestsChange: 8,
  issuesResolved: 342,
  issuesResolvedChange: 12,
  activeProjects: 48,
  activeProjectsChange: -2
}

const mockActivityData: ActivityData[] = Array.from({ length: 30 }, (_, i) => {
  const date = new Date()
  date.setDate(date.getDate() - (29 - i))
  // netCodeChange: สุ่มค่าระหว่าง -15000 ถึง +15000
  const netCodeChange = Math.floor(Math.random() * 300001);
  return {
    date: date.toISOString(),
    count: Math.floor(Math.random() * 100) + 50,
    netCodeChange
  }
})

const mockIssuesAnalysisData: IssuesAnalysisData = {
  stats: {
    totalOpen: 187,
    criticalHigh: {
      total: 10,
      critical: 4,
      high: 6
    },
    overdue: 34,
    projectCount: 21
  },
  recommendations: [
    {
      title: "Critical Issues Require Immediate Attention",
      description: "4 critical issues are open",
      priority: "critical",
      action: "Allocate senior developers to resolve critical issues immediately",
      context: "Projects: cyber-security-research, TBR-Oracle",
      icon: "alert"
    },
    {
      title: "Workload Imbalance Detected",
      description: "Henry Millard has 16 issues (2x average of 7.4)",
      priority: "high",
      action: "Redistribute issues to balance team workload",
      context: "Team member: Henry Millard",
      icon: "warning"
    },
    {
      title: "Stale Issues Need Review",
      description: "12 issues have had no activity in the last 14 days",
      priority: "medium",
      action: "Review and update status of stale issues",
      icon: "info"
    }
  ]
}

// Mock tech stack
export const mockTechStack: string[] = [
  'React', 'Node.js', 'TypeScript', 'Python', 'Django', 'PostgreSQL', 'Docker', 'GitLab CI'
];

export async function fetchTechStack(): Promise<string[]> {
  return Promise.resolve(mockTechStack);
}

// API functions
export async function fetchKPIData(): Promise<KPIData> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 1000))
  return mockKPIData
}

export async function fetchActivityData(): Promise<ActivityData[]> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 1000))
  return mockActivityData
}

export async function fetchGroupData(): Promise<GroupData[]> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 1000))
  return mockGroups
}

export async function fetchProjects(): Promise<ProjectData[]> {
  await new Promise(resolve => setTimeout(resolve, 1000))
  return mockProjects
}

export async function fetchContributors(): Promise<ContributorData[]> {
  await new Promise(resolve => setTimeout(resolve, 1000))
  return mockContributors
}

export async function fetchIssues(): Promise<IssueData[]> {
  await new Promise(resolve => setTimeout(resolve, 1000))
  return mockIssues
}

export async function fetchIssuesAnalysisData(): Promise<IssuesAnalysisData> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 1000))
  return mockIssuesAnalysisData
} 