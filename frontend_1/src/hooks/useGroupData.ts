import { useEffect, useState } from 'react';
import { fetchGroupData, GroupData } from '../services/dashboardApi';

export function useGroupData() {
  const [groupData, setGroupData] = useState<GroupData[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGroupData().then(data => {
      setGroupData(data);
      setLoading(false);
    });
  }, []);

  return { groupData, loading };
} 