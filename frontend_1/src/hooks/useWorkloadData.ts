import { useState, useEffect } from 'react';
import { fetchWorkloadTableData, WorkloadTableRow } from '../services/dashboardApi';

export function useWorkloadData() {
  const [data, setData] = useState<WorkloadTableRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const rows = await fetchWorkloadTableData();
        setData(rows);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load workload data');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return { data, loading, error };
} 