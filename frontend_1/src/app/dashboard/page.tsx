'use client'

import { useState, useEffect, useRef } from 'react'
import { Header } from '../../components/dashboard/Header'
import { KPISection } from '../../components/dashboard/KPISection'
import { ActivityChart } from '../../components/dashboard/ActivityChart'
import { GroupAnalysisSection } from '../../components/dashboard/GroupAnalysisSection'
import { IssuesAnalysisSection } from '../../components/dashboard/IssuesAnalysisSection'
import { HealthScoreMethodologySection } from '../../components/dashboard/HealthScoreMethodologySection'
import { ProjectPortfolioSection } from '../../components/dashboard/ProjectPortfolioSection'
import { TeamPerformanceSection } from '../../components/dashboard/TeamPerformanceSection'
import { IssuesManagementSection } from '../../components/dashboard/IssuesManagementSection'
import { useKPIData } from '../../hooks/useKPIData'
import { useActivityData, useActivityDetailData } from '../../hooks/useActivityData'
import { useGroupData } from '../../hooks/useGroupData'
import { useIssuesAnalysis } from '../../hooks/useIssuesAnalysis'
import { fetchProjects, fetchContributors } from '../../services/dashboardApi'
import { WorkloadTable } from '../../components/dashboard/WorkloadTable'
import { useWorkloadData } from '../../hooks/useWorkloadData'
import type { ActivityDetailData } from '../../services/dashboardApi'
import type { KPIData } from '../../services/dashboardApi'

function getKPIFromActivityDetail(data: ActivityDetailData[]): KPIData {
  let totalCommits = 0, mergeRequests = 0, issuesResolved = 0;
  const activeProjects = new Set<number>();
  data.forEach(day => {
    day.data.forEach(item => {
      totalCommits += item.commits;
      mergeRequests += item.mrs_created;
      issuesResolved += item.issues_closed;
      activeProjects.add(item.project_id);
    });
  });
  return {
    totalCommits,
    commitsChange: 0, // Not available for filtered
    mergeRequests,
    mergeRequestsChange: 0,
    issuesResolved,
    issuesResolvedChange: 0,
    activeProjects: activeProjects.size,
    activeProjectsChange: 0
  };
}

export default function DashboardPage() {
  const { kpiData, loading: kpiLoading } = useKPIData()
  const { groupData, loading: groupLoading } = useGroupData()
  const { issuesAnalysisData, loading: issuesLoading } = useIssuesAnalysis()

  // State สำหรับ filter user/project
  const [users, setUsers] = useState<{ id: number; name: string }[]>([])
  const [projects, setProjects] = useState<{ id: number; name: string }[]>([])
  const [selectedUsers, setSelectedUsers] = useState<number[]>([])
  const [selectedProjects, setSelectedProjects] = useState<number[]>([])
  const [filterLoading, setFilterLoading] = useState(false)
  // Metric filter state
  const metrics = [
    { value: 'commit', label: 'Commits' },
    { value: 'netCodeChange', label: 'Net Code Change' },
  ]
  const [selectedMetric, setSelectedMetric] = useState<string>('commit')

  // ใช้ useActivityData (ข้อมูล summary)
  const { data: filteredActivityData, loading: filteredActivityLoading } = useActivityDetailData({
    userIds: selectedUsers,
    projectIds: selectedProjects,
    days: 30
  });
  const { data: workloadData, loading: workloadLoading } = useWorkloadData();

  // --- Initial loading state ---
  const [initialLoading, setInitialLoading] = useState(true)
  useEffect(() => {
    if (!kpiLoading && !groupLoading && !issuesLoading) {
      setInitialLoading(false)
    }
  }, [kpiLoading, groupLoading, issuesLoading])
  // ----------------------------

  useEffect(() => {
    setFilterLoading(true)
    Promise.all([
      fetchContributors(),
      fetchProjects()
    ]).then(([contributors, projects]) => {
      setUsers(contributors.map((u: any) => ({ id: u.id, name: u.name })))
      setProjects(projects.map((p: any) => ({ id: p.id, name: p.name })))
    }).finally(() => setFilterLoading(false))
  }, [])

  // ฟังก์ชัน callback สำหรับ FilterBar
  const handleClearFilter = () => {
    setSelectedUsers([])
    setSelectedProjects([])
  }

  // --- Fix hydration mismatch: generate date only on client ---
  const [generatedAt, setGeneratedAt] = useState<string>('')
  useEffect(() => {
    setGeneratedAt(new Date().toLocaleString())
  }, [])
  // ----------------------------------------------------------

  // Tab bar
  const tabs = [
    { key: 'summary', label: 'Summary' },
    { key: 'group', label: 'Group Analysis' },
    { key: 'issues', label: 'Issues Analysis' },
    { key: 'portfolio', label: 'Project Portfolio' },
    { key: 'team', label: 'Team Performance' },
    { key: 'issuesMgmt', label: 'Issues Management' },
  ];
  const [activeTab, setActiveTab] = useState('summary');

  if (initialLoading) {
    return (
      <div className="min-h-screen bg-background">
        <Header 
          title="Executive Dashboard"
          subtitle="Development Team • 30 Day Analysis"
          meta={{
            generatedAt: generatedAt || '...',
            projectCount: undefined
          }}
        />
        <main className="w-full max-w-none px-8 py-6 space-y-6">
          <div className="animate-pulse space-y-4">
            <div className="h-32 bg-muted rounded-lg" />
            <div className="h-[300px] bg-muted rounded-lg" />
            <div className="h-[400px] bg-muted rounded-lg" />
            <div className="h-[300px] bg-muted rounded-lg" />
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Header 
        title="Executive Dashboard"
        subtitle="Development Team • 30 Day Analysis"
        meta={{
          generatedAt: generatedAt || '...',
          projectCount: kpiData?.activeProjects ?? 0
        }}
      />
      {/* Tab Bar */}
      <div className="flex justify-center gap-6 border-b mb-2">
        {tabs.map(tab => (
          <button
            key={tab.key}
            className={`px-4 py-2 font-semibold transition-colors duration-150 ${activeTab === tab.key ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500 hover:text-blue-500'}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <main className="w-full max-w-none px-8 pt-0 pb-6 space-y-6">
        {activeTab === 'summary' && (
          <div className="flex gap-6">
            {/* ซ้าย 75% */}
            <div className="w-3/5 flex flex-col gap-4">
              {(selectedUsers.length > 0 || selectedProjects.length > 0)
                ? <KPISection data={getKPIFromActivityDetail(filteredActivityData)} />
                : (kpiData && <KPISection data={kpiData} />)
              }
              <ActivityChart
                data={filteredActivityData}
                chartType={selectedMetric as 'commit' | 'netCodeChange'}
                users={users}
                projects={projects}
                metrics={metrics}
                selectedUsers={selectedUsers}
                selectedProjects={selectedProjects}
                selectedMetric={selectedMetric}
                onChangeUsers={setSelectedUsers}
                onChangeProjects={setSelectedProjects}
                onChangeMetric={setSelectedMetric}
                onClear={handleClearFilter}
                isLoading={filterLoading || filteredActivityLoading}
              />
            </div>
            {/* ขวา 25% */}
            <div className="w-2/5 flex flex-col">
              <div className="rounded-2xl border border-black bg-background flex flex-col p-0 overflow-hidden max-h-[665px]">
                <div className="px-4 py-2 border-b border-black font-bold text-base">Workload</div>
                <div className="flex-1 overflow-auto">
                  <WorkloadTable data={workloadData} loading={workloadLoading} />
                </div>
              </div>
            </div>
          </div>
        )}
        {activeTab === 'group' && groupData && <GroupAnalysisSection groups={groupData} />}
        {activeTab === 'issues' && issuesAnalysisData && (
          <IssuesAnalysisSection 
            stats={issuesAnalysisData.stats}
            recommendations={issuesAnalysisData.recommendations}
          />
        )}
        {activeTab === 'portfolio' && (
          <>
            <ProjectPortfolioSection />
            <div className="mt-6">
              <HealthScoreMethodologySection />
            </div>
          </>
        )}
        {activeTab === 'team' && <TeamPerformanceSection />}
        {activeTab === 'issuesMgmt' && <IssuesManagementSection />}
      </main>
    </div>
  )
} 