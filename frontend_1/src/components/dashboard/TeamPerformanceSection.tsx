import React from 'react';
import { ContributorData } from '../../services/dashboardApi';
import { useContributors } from '../../hooks/useContributors';

function getInitials(name: string | undefined) {
  if (!name) return '?';
  return name
    .split(' ')
    .map((n) => n[0]?.toUpperCase() || '')
    .join('')
    .slice(0, 2);
}

function ContributorCard({ contributor }: { contributor: ContributorData }) {
  // Show up to 5 projects, rest as "+N more"
  const maxProjects = 5;
  const shownProjects = contributor.activeProjects.slice(0, maxProjects);
  const moreCount = contributor.activeProjects.length - maxProjects;

  return (
    <div className="bg-white dark:bg-card rounded-lg shadow p-6 border border-muted flex flex-col h-full min-w-[270px]">
      {/* Avatar & Name */}
      <div className="flex items-center gap-4 mb-2">
        <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center text-xl font-bold text-primary">
          {getInitials(contributor.name)}
        </div>
        <div>
          <div className="text-base font-bold leading-tight">{contributor.name}</div>
          <div className="text-xs text-muted-foreground mt-0.5">{contributor.commits} commits · {contributor.issues} issues · {contributor.projects} projects</div>
        </div>
      </div>
      <hr className="my-3 border-muted-foreground/20" />
      {/* Active Projects */}
      <div className="mb-2">
        <div className="text-sm font-semibold mb-1">Active Projects:</div>
        <div className="flex flex-wrap gap-2">
          {shownProjects.map((proj) => (
            <span key={proj} className="bg-muted text-xs px-2 py-1 rounded font-medium border border-muted-foreground/10">{proj}</span>
          ))}
          {moreCount > 0 && (
            <span className="bg-muted text-xs px-2 py-1 rounded font-medium border border-muted-foreground/10">+{moreCount} more</span>
          )}
        </div>
      </div>
      <hr className="my-3 border-muted-foreground/20" />
      {/* Workload */}
      <div className="mb-1 text-sm font-semibold">Current Workload:</div>
      <div className="flex flex-row justify-between text-center mb-2">
        <div className="flex-1">
          <div className="text-base font-bold">{contributor.workload.openIssues}</div>
          <div className="text-xs text-muted-foreground">Open Issues</div>
        </div>
        <div className="flex-1">
          <div className="text-base font-bold">{contributor.workload.resolved}</div>
          <div className="text-xs text-muted-foreground">Resolved</div>
        </div>
        <div className="flex-1">
          <div className="text-base font-bold">{contributor.workload.mrs}</div>
          <div className="text-xs text-muted-foreground">MRs</div>
        </div>
      </div>
      {/* Net Change */}
      <div className="mt-2">
        <div className="text-sm font-semibold mb-1">Net Change:</div>
        <div className="flex flex-row justify-between text-center">
          {(['7d', '15d', '30d'] as const).map((period) => {
            const data = contributor.netChange[period];
            return (
              <div key={period} className="flex-1">
                <div className="text-base font-bold">
                  {data.net > 0 ? '+' : ''}{data.net}
                </div>
                <div className="text-xs">
                  <span className="text-muted-foreground">(</span>
                  <span className="text-green-600">+{data.additions}</span>
                  <span className="text-muted-foreground">, </span>
                  <span className="text-red-600">-{data.deletions}</span>
                  <span className="text-muted-foreground">)</span>
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">{period.toUpperCase()}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function TeamPerformanceSection() {
  const { contributors, loading } = useContributors();

  return (
    <section className="bg-card text-card-foreground p-6 rounded-lg shadow-sm mt-0">
      <h3 className="text-2xl font-bold mb-6">Team Performance</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {contributors.length === 0 ? (
          <div className="col-span-full text-center text-muted-foreground py-8">No contributors found.</div>
        ) : (
          contributors.map(contributor => (
            <ContributorCard key={contributor.id} contributor={contributor} />
          ))
        )}
      </div>
    </section>
  );
}

export default TeamPerformanceSection; 