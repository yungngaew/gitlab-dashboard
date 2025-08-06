import React from 'react';
import { ProjectData } from '../../services/dashboardApi';

// ไอคอน SVG เล็ก ๆ สำหรับแต่ละ stat
const IconCommits = () => (
  <svg className="w-4 h-4 mr-1 inline-block" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><path d="M12 8v4l3 3" /></svg>
);
const IconMRs = () => (
  <svg className="w-4 h-4 mr-1 inline-block" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M17 7v6a4 4 0 01-4 4H7" /><path d="M7 17l-4-4 4-4" /></svg>
);
const IconContributors = () => (
  <svg className="w-4 h-4 mr-1 inline-block" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="9" cy="7" r="4" /><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" /><circle cx="17" cy="17" r="4" /></svg>
);
const IconIssues = () => (
  <svg className="w-4 h-4 mr-1 inline-block" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><path d="M12 8v4" /><circle cx="12" cy="16" r="1" /></svg>
);

// กราฟแท่ง placeholder
const BarChartPlaceholder = () => (
  <div className="flex items-end gap-1 h-8 mt-2">
    <div className="w-2 h-4 bg-muted rounded-sm" />
    <div className="w-2 h-6 bg-muted rounded-sm" />
    <div className="w-2 h-3 bg-muted rounded-sm" />
    <div className="w-2 h-7 bg-muted rounded-sm" />
    <div className="w-2 h-5 bg-muted rounded-sm" />
  </div>
);

interface ProjectCardProps {
  project: ProjectData;
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <div className="bg-white dark:bg-card rounded-lg shadow p-5 border border-muted flex flex-col h-full">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold">{project.name}</span>
          <span className={`px-2 py-1 text-xs rounded font-bold ml-2 ${project.status === 'active' ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' : 'bg-gray-200 text-gray-600 dark:bg-gray-800 dark:text-gray-300'}`}>{project.status === 'active' ? 'Active' : project.status.charAt(0).toUpperCase() + project.status.slice(1)}</span>
        </div>
        <span className={`px-2 py-1 text-xs rounded font-bold ${project.grade === 'A+' ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' : project.grade === 'A' ? 'bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400' : project.grade === 'B' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300' : project.grade === 'C' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300' : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'}`}>{project.grade}</span>
      </div>
      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{project.description}</p>
      <div className="flex flex-wrap sm:flex-nowrap gap-x-2 gap-y-1 w-full text-xs mb-2 justify-start">
        <div className="flex items-center flex-1 min-w-[100px] max-w-[160px] sm:flex-none sm:min-w-0 sm:max-w-none"><IconCommits />{project.commits} <span className="ml-1 text-muted-foreground">commits</span></div>
        <div className="flex items-center flex-1 min-w-[100px] max-w-[160px] sm:flex-none sm:min-w-0 sm:max-w-none"><IconMRs />{project.mergeRequests} <span className="ml-1 text-muted-foreground">MRs</span></div>
        <div className="flex items-center flex-1 min-w-[100px] max-w-[160px] sm:flex-none sm:min-w-0 sm:max-w-none"><IconContributors />{project.contributors} <span className="ml-1 text-muted-foreground">contributors</span></div>
        <div className="flex items-center flex-1 min-w-[100px] max-w-[160px] sm:flex-none sm:min-w-0 sm:max-w-none"><IconIssues />{project.issues} <span className="ml-1 text-muted-foreground">issues</span></div>
      </div>
      <BarChartPlaceholder />
    </div>
  );
}

export default ProjectCard; 