import { useEffect, useState } from 'react';
import { fetchContributors, ContributorData } from '../services/dashboardApi';

export function useContributors() {
  const [contributors, setContributors] = useState<ContributorData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchContributors().then(data => {
      setContributors(data);
      setLoading(false);
    });
  }, []);

  return { contributors, loading };
} 