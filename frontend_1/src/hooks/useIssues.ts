import { useEffect, useState } from 'react';
import { fetchIssues, IssueData } from '../services/dashboardApi';

export function useIssues() {
  const [issues, setIssues] = useState<IssueData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchIssues().then(data => {
      setIssues(data.filter(issue => issue.status === 'opened'));
      setLoading(false);
    });
  }, []);

  return { issues, loading };
} 