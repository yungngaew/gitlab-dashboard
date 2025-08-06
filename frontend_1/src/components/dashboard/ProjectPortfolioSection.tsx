import React, { useState } from 'react';
import { ProjectData } from '../../services/dashboardApi';
import { useProjects } from '../../hooks/useProjects';
import ProjectCard from './ProjectCard';
import { HealthScoreMethodologySection } from './HealthScoreMethodologySection';

export function ProjectPortfolioSection() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [gradeFilter, setGradeFilter] = useState('all');
  const { projects, loading } = useProjects();

  // Filter projects (search, status, grade)
  const filtered = projects.filter(p => {
    const matchesSearch =
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.description.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || p.status === statusFilter;
    const matchesGrade = gradeFilter === 'all' || p.grade === gradeFilter;
    return matchesSearch && matchesStatus && matchesGrade;
  });

  return (
    <section className="bg-card text-card-foreground p-2 sm:p-6 rounded-lg shadow-sm mt-0 w-full max-w-full">
      <h3 className="text-2xl font-bold mb-6">Project Portfolio</h3>
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 sm:gap-4 mb-6 w-full max-w-full">
        {/* Search box */}
        <div className="flex-1">
          <input
            id="project-search"
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search projects..."
            className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring focus:border-primary"
          />
        </div>
        {/* Filters */}
        <div className="flex gap-2 md:ml-4 mt-2 md:mt-0">
          <select
            id="status-filter"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="px-3 py-2 border rounded-md focus:outline-none focus:ring focus:border-primary min-w-[140px]"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="maintenance">Maintenance</option>
            <option value="inactive">Inactive</option>
          </select>
          <select
            id="grade-filter"
            value={gradeFilter}
            onChange={e => setGradeFilter(e.target.value)}
            className="px-3 py-2 border rounded-md focus:outline-none focus:ring focus:border-primary min-w-[100px]"
          >
            <option value="all">All Grades</option>
            <option value="A+">A+</option>
            <option value="A">A</option>
            <option value="B">B</option>
            <option value="C">C</option>
            <option value="D/F">D/F</option>
          </select>
        </div>
      </div>
      {/* Project card grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 w-full max-w-full">
        {filtered.length === 0 ? (
          <div className="col-span-full text-center text-muted-foreground py-8">No projects found.</div>
        ) : (
          filtered.map(project => (
            <ProjectCard key={project.id} project={project} />
          ))
        )}
      </div>
    </section>
  );
}

export default ProjectPortfolioSection; 