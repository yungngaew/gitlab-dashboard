import { useEffect, useState } from 'react';
import { fetchProjects, ProjectData } from '../services/dashboardApi';

export function useProjects() {
  const [projects, setProjects] = useState<ProjectData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProjects().then(data => {
      setProjects(data);
      setLoading(false);
    });
  }, []);

  return { projects, loading };
} 