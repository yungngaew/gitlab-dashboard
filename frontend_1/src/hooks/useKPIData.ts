import { useEffect, useState } from 'react';
import { fetchKPIData, KPIData } from '../services/dashboardApi';

export function useKPIData() {
  const [kpiData, setKPIData] = useState<KPIData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchKPIData().then(data => {
      setKPIData(data);
      setLoading(false);
    });
  }, []);

  return { kpiData, loading };
} 