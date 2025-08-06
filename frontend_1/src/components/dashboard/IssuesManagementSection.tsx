import React, { useState, useMemo } from 'react';
import { IssueData } from '../../services/dashboardApi';
import { useIssues } from '../../hooks/useIssues';
import { AutocompleteDropdown } from './FilterBar';

function getInitials(name: string) {
  if (!name) return '';
  const parts = name.split(' ');
  if (parts.length === 1) return parts[0][0].toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function IssuesManagementSection() {
  const [search, setSearch] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [assigneeFilter, setAssigneeFilter] = useState('all');
  const [projectFilter, setProjectFilter] = useState('all');
  const { issues, loading } = useIssues();
  const [sortBy, setSortBy] = useState<'priority' | 'age' | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  // Calculate stats from real data
  const stats = useMemo(() => {
    const totalOpen = issues.length;
    const critical = issues.filter(issue => issue.priority === 'critical').length;
    const overdue = issues.filter(issue => isOverdue(issue)).length;
    const unassigned = issues.filter(issue => !issue.assignee || issue.assignee === 'Unassigned').length;
    
    return { totalOpen, critical, overdue, unassigned };
  }, [issues]);

  // Get unique assignees and projects for filter options
  const assignees = useMemo(() => {
    const uniqueAssignees = [...new Set(issues.map(issue => issue.assignee).filter(Boolean))];
    return uniqueAssignees.sort();
  }, [issues]);

  const projects = useMemo(() => {
    const uniqueProjects = [...new Set(issues.map(issue => issue.project).filter(Boolean))];
    return uniqueProjects.sort();
  }, [issues]);

  const assigneeOptions = assignees.map((a, i) => ({ id: i + 1, name: a }));
  const projectOptions = projects.map((p, i) => ({ id: i + 1, name: p }));
  const [selectedAssignees, setSelectedAssignees] = useState<number[]>([]);
  const [selectedProjects, setSelectedProjects] = useState<number[]>([]);

  // Helper: check if overdue (use due_date only)
  function isOverdue(issue: IssueData) {
    if (!issue.due_date) return false;
    const due = new Date(issue.due_date);
    const now = new Date();
    return due < now;
  }

  // Filtering logic
  const filteredIssues = issues.filter(issue => {
    const matchesSearch =
      search === '' ||
      issue.title.toLowerCase().includes(search.toLowerCase()) ||
      issue.project.toLowerCase().includes(search.toLowerCase());
    const matchesPriority = priorityFilter === 'all' || issue.priority === priorityFilter;
    const matchesAssignee = selectedAssignees.length === 0 || selectedAssignees.some(id => assigneeOptions[id - 1]?.name === issue.assignee);
    const matchesProject = selectedProjects.length === 0 || selectedProjects.some(id => projectOptions[id - 1]?.name === issue.project);
    return matchesSearch && matchesPriority && matchesAssignee && matchesProject;
  });

  // Sorting logic
  const sortedIssues = [...filteredIssues].sort((a, b) => {
    if (!sortBy) return 0;
    if (sortBy === 'priority') {
      const order = ['critical', 'high', 'medium', 'low'];
      const diff = order.indexOf(a.priority) - order.indexOf(b.priority);
      return sortDir === 'asc' ? diff : -diff;
    }
    if (sortBy === 'age') {
      const ageA = new Date().getTime() - new Date(a.createdAt).getTime();
      const ageB = new Date().getTime() - new Date(b.createdAt).getTime();
      return sortDir === 'asc' ? ageA - ageB : ageB - ageA;
    }
    return 0;
  });

  if (loading) {
    return (
      <section className="bg-white text-card-foreground p-2 sm:p-6 rounded-lg shadow-sm mt-8 w-full max-w-full">
        <h3 className="text-2xl font-bold mb-6">Issues Management</h3>
        <div className="animate-pulse space-y-4">
          <div className="h-12 bg-gray-200 rounded"></div>
          <div className="h-8 bg-gray-200 rounded"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </section>
    );
  }

  return (
    <section className="bg-white text-card-foreground p-2 sm:p-6 rounded-lg shadow-sm mt-0 w-full max-w-full">
      <h3 className="text-2xl font-bold mb-4">Issues Management</h3>
      {/* Filters */}
      <div className="flex flex-row items-center gap-2 mb-4 w-full max-w-full">
        <input
          id="issue-search"
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search issues..."
          className="flex-1 px-4 py-2 border rounded-md focus:outline-none focus:ring focus:border-primary text-base h-11 min-w-[140px]"
        />
        <select
          id="priority-filter"
          value={priorityFilter}
          onChange={e => setPriorityFilter(e.target.value)}
          className="flex-1 px-4 py-2 border rounded-md focus:outline-none focus:ring focus:border-primary min-w-[100px] text-base h-11"
        >
          <option value="all">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <AutocompleteDropdown
          options={assigneeOptions}
          selected={selectedAssignees}
          onChange={setSelectedAssignees}
          placeholder="Select assignee(s)..."
          label="Assignee"
          multi={true}
          className="flex-1 min-w-[100px] h-11 [&>label]:sr-only"
        />
        <AutocompleteDropdown
          options={projectOptions}
          selected={selectedProjects}
          onChange={setSelectedProjects}
          placeholder="Select project(s)..."
          label="Project"
          multi={true}
          className="flex-1 min-w-[100px] h-11 [&>label]:sr-only"
        />
      </div>
      {/* Stats Bar */}
      <div className="flex flex-wrap gap-4 sm:gap-12 mb-4 w-full max-w-full">
        <div className="flex flex-col items-start">
          <span className="text-3xl font-bold leading-tight">{stats.totalOpen}</span>
          <span className="text-sm text-gray-500 mt-1">Total Open</span>
        </div>
        <div className="flex flex-col items-start">
          <span className="text-3xl font-bold leading-tight">{stats.critical}</span>
          <span className="text-sm text-gray-500 mt-1">Critical</span>
        </div>
        <div className="flex flex-col items-start">
          <span className="text-3xl font-bold leading-tight">{stats.overdue}</span>
          <span className="text-sm text-gray-500 mt-1">Overdue</span>
        </div>
        <div className="flex flex-col items-start">
          <span className="text-3xl font-bold leading-tight">{stats.unassigned}</span>
          <span className="text-sm text-gray-500 mt-1">Unassigned</span>
        </div>
      </div>
      {/* Issues Table */}
      <div className="overflow-x-auto w-full max-w-full">
        <table className="min-w-0 w-full border border-gray-200 rounded-lg text-xs sm:text-sm">
          <thead>
            <tr className="bg-blue-50">
              <th className="px-4 py-3 text-left text-sm font-bold text-gray-700 cursor-pointer select-none" onClick={() => {
                if (sortBy === 'priority') setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
                setSortBy('priority');
              }}>
                Priority {sortBy === 'priority' ? (sortDir === 'asc' ? '▲' : '▼') : ''}
              </th>
              <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">Issue</th>
              <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">Project</th>
              <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">Assignee</th>
              <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">Due Date</th>
              <th className="px-4 py-3 text-left text-sm font-bold text-gray-700 cursor-pointer select-none" onClick={() => {
                if (sortBy === 'age') setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
                setSortBy('age');
              }}>
                Age {sortBy === 'age' ? (sortDir === 'asc' ? '▲' : '▼') : ''}
              </th>
              <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">Labels</th>
            </tr>
          </thead>
          <tbody>
            {sortedIssues.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center text-muted-foreground py-6">No issues found.</td>
              </tr>
            ) : (
              sortedIssues.map(issue => {
                // Calculate age in days
                const created = new Date(issue.createdAt);
                const now = new Date();
                const age = Math.floor((now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24));
                // Priority badge color
                let priorityColor = 'bg-gray-300 text-gray-800';
                if (issue.priority === 'critical') priorityColor = 'bg-red-600 text-white';
                else if (issue.priority === 'high') priorityColor = 'bg-red-400 text-white';
                else if (issue.priority === 'medium') priorityColor = 'bg-yellow-400 text-white';
                // Overdue row highlight
                const overdue = isOverdue(issue);
                return (
                  <tr key={issue.id} className={overdue ? 'bg-red-100' : ''}>
                    <td className="px-4 py-2">
                      <span className={`px-3 py-1 rounded font-bold text-xs ${priorityColor}`}>{issue.priority.toUpperCase()}</span>
                    </td>
                    <td className="px-4 py-2">{issue.title}</td>
                    <td className="px-4 py-2">{issue.project}</td>
                    <td className="px-4 py-2">
                      {issue.assignee && issue.assignee !== 'Unassigned' ? (
                        <span className="flex items-center gap-2">
                          <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-200 text-gray-700 font-bold text-base">
                            {getInitials(issue.assignee)}
                          </span>
                          <span>{issue.assignee}</span>
                        </span>
                      ) : (
                        <span className="italic text-gray-400">Unassigned</span>
                      )}
                    </td>
                    <td className={`px-4 py-2 font-semibold ${overdue ? 'text-red-600' : ''}`}>
                      {issue.due_date
                        ? new Date(issue.due_date).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
                        : '-'}
                    </td>
                    <td className="px-4 py-2">{age}d</td>
                    <td className="px-4 py-2">
                      {Array.isArray(issue.labels) && issue.labels.length > 0
                        ? issue.labels.map((label: string, idx: number) => (
                            <span key={idx} className="inline-block bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-semibold mr-1 mb-1">{label}</span>
                          ))
                        : '-'}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default IssuesManagementSection; 