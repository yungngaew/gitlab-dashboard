// Real API service for dashboard data

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
  netCodeChange?: number
}

export interface ActivityDetailData {
  date: string
  data: Array<{
    user_id: number
    user_name: string
    project_id: number
    project_name: string
    commits: number
    issues_created: number
    issues_closed: number
    mrs_created: number
    mrs_merged: number
  }>
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
  status: 'opened' | 'closed' | 'in_progress'
  priority: 'low' | 'medium' | 'high' | 'critical'
  createdAt: string
  updatedAt: string
  due_date?: string
  labels?: string[]
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

export interface ActivitySummaryData {
  date: string;
  commits: number;
  issues_created: number;
  issues_closed: number;
  mrs_created: number;
  mrs_merged: number;
  last_updated?: string;
}

export interface WorkloadTableRow {
  author_name: string
  open: number | null
  inProgress: number | null
  total: number | null
}

// Utility: fetch with timeout
export async function fetchWithTimeout(resource: RequestInfo, options: any = {}) {
  const { timeout = 60000, ...rest } = options; // default 60 seconds
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(resource, {
      ...rest,
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response;
  } finally {
    clearTimeout(id);
  }
}

// Base API URL - adjust this to match your backend server
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
// Fetch KPI summary data
export async function fetchKPIData(): Promise<KPIData> {
  try {
    const res = await fetchWithTimeout(`/api/database/kpi`, { timeout: 60000 });
    const json = await res.json();
    
    if (!json.kpi) {
      // Fallback to summary endpoint
      const summaryRes = await fetchWithTimeout(`/api/database/summary`, { timeout: 60000 });
      const summaryJson = await summaryRes.json();
      const s = summaryJson.summary;
      
      return {
        totalCommits: s?.total_commits || 0,
        commitsChange: 0, // Not available in API
        mergeRequests: s?.total_mrs || 0,
        mergeRequestsChange: 0,
        issuesResolved: s?.total_issues || 0,
        issuesResolvedChange: 0,
        activeProjects: s?.active_projects || 0,
        activeProjectsChange: 0
      };
    }
    
    const kpi = json.kpi;
    return {
      totalCommits: kpi.total_commits || 0,
      commitsChange: 0, // Not available in API
      mergeRequests: kpi.total_mrs || 0,
      mergeRequestsChange: 0,
      issuesResolved: kpi.total_issues || 0,
      issuesResolvedChange: 0,
      activeProjects: kpi.active_projects || 0,
      activeProjectsChange: 0
    };
  } catch (error) {
    console.error('Error fetching KPI data:', error);
    return {
      totalCommits: 0,
      commitsChange: 0,
      mergeRequests: 0,
      mergeRequestsChange: 0,
      issuesResolved: 0,
      issuesResolvedChange: 0,
      activeProjects: 0,
      activeProjectsChange: 0
    };
  }
}

// Fetch all projects
export async function fetchProjects(): Promise<ProjectData[]> {
  try {
    const res = await fetchWithTimeout(`/api/database/projects`, { timeout: 60000 });
    const json = await res.json();
    return (json.projects || []).map((p: any) => ({
      id: p.id,
      name: p.name,
      group: p.group_name || '',
      status: p.status || 'active',
      grade: p.health_grade || 'C',
      description: p.description || '',
      issues: p.open_issues || 0,
      mergeRequests: p.mrs_created || 0,
      commits: p.commits_30d || 0,
      contributors: p.contributors_30d || 0,
      lastActivity: p.last_activity || ''
    }));
  } catch (error) {
    console.error('Error fetching projects:', error);
    return [];
  }
}

// Fetch contributors/team data
export async function fetchContributors(): Promise<ContributorData[]> {
  try {
    const res = await fetchWithTimeout(`/api/database/team-members`, { timeout: 60000 });
    const json = await res.json();
    
    // Get project assignments for each member
    const projectAssignmentsRes = await fetchWithTimeout(`/api/database/team-member-projects`, { timeout: 60000 });
    const projectAssignmentsJson = await projectAssignmentsRes.json();
    const projectAssignments = projectAssignmentsJson.assignments || {};
    
    return (json.team_members || []).map((member: any, index: number) => {
      const memberProjects = projectAssignments[member.id] || [];
      
      return {
        id: member.id || index + 1,
        name: member.name || member.username || 'Unknown',
        email: member.email || '',
        commits: member.commits || 0,
        issues: member.issues_assigned || 0,
        mergeRequests: member.merge_requests || 0,
        lastActivity: member.last_activity || '',
        projects: memberProjects.length,
        activeProjects: memberProjects.map((p: any) => p.project_name || 'Unknown'),
        workload: {
          openIssues: member.issues_assigned || 0,
          resolved: member.issues_resolved || 0,
          mrs: member.merge_requests || 0
        },
        netChange: {
          '7d': { net: 0, additions: 0, deletions: 0 },
          '15d': { net: 0, additions: 0, deletions: 0 },
          '30d': { net: 0, additions: 0, deletions: 0 }
        }
      };
    });
  } catch (error) {
    console.error('Error fetching contributors:', error);
    return [];
  }
}

// Fetch issues
export async function fetchIssues(): Promise<IssueData[]> {
  try {
    const res = await fetchWithTimeout(`/api/database/issues`, { timeout: 60000 });
    const json = await res.json();
    return (json.issues || []).map((i: any) => ({
      id: i.id,
      title: i.title,
      project: i.project_name || 'Unknown Project',
      assignee: i.assignee_name || 'Unassigned',
      status: i.state || 'open',
      priority: i.priority,
      createdAt: i.created_at,
      updatedAt: i.updated_at,
      due_date: i.due_date,
      labels: i.labels || []
    }));
  } catch (error) {
    console.error('Error fetching issues:', error);
    return [];
  }
}

// Fetch issues analysis (recommendations, stats)
export async function fetchIssuesAnalysisData(): Promise<IssuesAnalysisData> {
  try {
    const res = await fetchWithTimeout(`/api/database/issues`, { timeout: 60000 });
    const json = await res.json();
    const issues = json.issues || [];

    // Calculate stats from issues data
    const totalOpen = issues.filter((i: any) => i.state === 'open').length;
    const criticalIssues = issues.filter((i: any) => i.priority === 'critical' && i.state === 'open').length;
    const highIssues = issues.filter((i: any) => i.priority === 'high' && i.state === 'open').length;
    
    // Calculate overdue issues (due_date < today and state = 'open')
    const today = new Date().toISOString().split('T')[0];
    const overdueIssues = issues.filter((i: any) => 
      i.state === 'open' && i.due_date && i.due_date < today
    ).length;
    
    // Get unique projects
    const projectCount = new Set(issues.map((i: any) => i.project_name)).size;

    return {
      stats: {
        totalOpen,
        criticalHigh: {
          total: criticalIssues + highIssues,
          critical: criticalIssues,
          high: highIssues
        },
        overdue: overdueIssues,
        projectCount
      },
      recommendations: [
        {
          title: "Critical Issues Require Immediate Attention",
          description: `${criticalIssues} critical issues are open`,
          priority: "critical" as const,
          action: "Allocate senior developers to resolve critical issues immediately",
          context: `Total critical issues: ${criticalIssues}`,
          icon: "alert" as const
        },
        {
          title: "High Priority Issues Need Review",
          description: `${highIssues} high priority issues are open`,
          priority: "high" as const,
          action: "Review and prioritize high priority issues",
          context: `Total high priority issues: ${highIssues}`,
          icon: "warning" as const
        },
        {
          title: "Overdue Issues Require Attention",
          description: `${overdueIssues} issues are overdue`,
          priority: "high" as const,
          action: "Review and update overdue issues",
          context: `Total overdue issues: ${overdueIssues}`,
          icon: "warning" as const
        }
      ].filter(rec => {
        if (rec.priority === 'critical') return criticalIssues > 0;
        if (rec.priority === 'high') return highIssues > 0 || overdueIssues > 0;
        return true;
      })
    };
  } catch (error) {
    console.error('Error fetching issues analysis:', error);
    return {
      stats: {
        totalOpen: 0,
        criticalHigh: {
          total: 0,
          critical: 0,
          high: 0
        },
        overdue: 0,
        projectCount: 0
      },
      recommendations: []
    };
  }
}

// Fetch group data
export async function fetchGroupData(): Promise<GroupData[]> {
  try {
    const res = await fetchWithTimeout(`/api/database/groups`, { timeout: 60000 });
    const json = await res.json();
    
    // Get project counts for each group
    const projectCountsRes = await fetchWithTimeout(`/api/database/group-project-counts`, { timeout: 60000 });
    const projectCountsJson = await projectCountsRes.json();
    const projectCounts = projectCountsJson.counts || {};
    
    return (json.groups || []).map((g: any) => ({
      name: g.name || 'Unknown Group',
      health: g.health_grade || 'C',
      projectCount: projectCounts[g.id] || 0,
      commitCount: g.total_commits || 0,
      activeUsers: g.active_users || 0
    }));
  } catch (error) {
    console.error('Error fetching group data:', error);
    return [];
  }
}

// Fetch activity data (daily commits)
export async function fetchActivityData(): Promise<ActivitySummaryData[]> {
  try {
    const res = await fetchWithTimeout(`/api/database/activity`, { timeout: 60000 });
    const json = await res.json();
    // return array ที่มีข้อมูลครบทุก field จาก json.activity
    return (json.activity || []).map((a: any) => ({
      date: a.date,
      commits: a.commits || 0,
      issues_created: a.issues_created || 0,
      issues_closed: a.issues_closed || 0,
      mrs_created: a.mrs_created || 0,
      mrs_merged: a.mrs_merged || 0,
      last_updated: a.last_updated || null
    }));
  } catch (error) {
    console.error('Error fetching activity data:', error);
    return [];
  }
}

// Fetch detailed activity data with user and project filters
export async function fetchActivityDetailData(
  options: {
    userIds?: number[]
    projectIds?: number[]
    days?: number
  } = {}
): Promise<ActivityDetailData[]> {
  try {
    const { userIds, projectIds, days = 30 } = options;
    // Build query parameters
    const params = new URLSearchParams();
    if (userIds && userIds.length > 0) {
      params.append('user_ids', userIds.join(','));
    }
    if (projectIds && projectIds.length > 0) {
      params.append('project_ids', projectIds.join(','));
    }
    params.append('days', days.toString());
    // Use the correct endpoint
    const url = `/api/database/activity-detail?${params.toString()}`;
    const res = await fetchWithTimeout(url, { timeout: 60000 });
    const json = await res.json();
    // The backend returns { activity_detail: [...], ... }
    return json.activity_detail || [];
  } catch (error) {
    console.error('Error fetching activity detail data:', error);
    return [];
  }
} 

export async function fetchWorkloadTableData(): Promise<WorkloadTableRow[]> {
  const issues = await fetchIssues();
  const map: Record<string, { open: number; inProgress: number }> = {};
  for (const issue of issues) {
    const name = issue.assignee || '-';
    if (!map[name]) {
      map[name] = { open: 0, inProgress: 0 };
    }
    if (issue.status === 'opened') {
      const labels: string[] = Array.isArray(issue.labels) ? issue.labels : [];
      const isInProgress = labels.some(l => {
        const lower = l.toLowerCase();
        return lower === 'in progress' || lower === 'in-progress';
      });
      if (isInProgress) {
        map[name].inProgress += 1;
      } else {
        map[name].open += 1;
      }
    }
  }
  return Object.entries(map)
    .filter(([_, v]) => v.open > 0 || v.inProgress > 0)
    .map(([author_name, v]) => ({
      author_name,
      open: v.open,
      inProgress: v.inProgress,
      total: v.open + v.inProgress,
    }));
} 