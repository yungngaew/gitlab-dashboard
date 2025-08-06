import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Line,
} from 'recharts'
import { FilterBar } from './FilterBar';
import type { ActivitySummaryData, ActivityDetailData } from '../../services/dashboardApi';
import { eachDayOfInterval, format, parseISO } from 'date-fns';

type ActivityChartData = ActivitySummaryData | ActivityDetailData;

interface ActivityChartProps {
  data: ActivitySummaryData[] | ActivityDetailData[];
  chartType: 'commit' | 'netCodeChange';
  users: { id: number; name: string }[];
  projects: { id: number; name: string }[];
  metrics: { value: string; label: string }[];
  selectedUsers: number[];
  selectedProjects: number[];
  selectedMetric: string;
  onChangeUsers: (userIds: number[]) => void;
  onChangeProjects: (projectIds: number[]) => void;
  onChangeMetric: (metric: string) => void;
  onClear: () => void;
  isLoading?: boolean;
}

export function ActivityChart({
  data,
  chartType,
  users,
  projects,
  metrics,
  selectedUsers,
  selectedProjects,
  selectedMetric,
  onChangeUsers,
  onChangeProjects,
  onChangeMetric,
  onClear,
  isLoading = false,
}: ActivityChartProps) {
  // Transform detailed data to chart format
  const chartData = React.useMemo(() => {
    if (!data || data.length === 0) return [];

    // Detect if data is ActivityDetailData[] (filtered) or ActivitySummaryData[] (unfiltered)
    const isDetail = (d: any): d is ActivityDetailData => Array.isArray(d.data);

    // Flatten to summary per day
    let summaryByDate: Record<string, { commits: number; netCodeChange?: number }> = {};

    if (isDetail(data[0])) {
      // ActivityDetailData[]
      (data as ActivityDetailData[]).forEach(day => {
        let commits = 0;
        // Optionally, sum netCodeChange if available in your backend
        day.data.forEach(item => {
          commits += item.commits || 0;
        });
        summaryByDate[day.date] = { commits };
      });
    } else {
      // ActivitySummaryData[]
      (data as ActivitySummaryData[]).forEach(day => {
        summaryByDate[day.date] = { commits: day.commits, netCodeChange: (day as any).netCodeChange };
      });
    }

    const dates = Object.keys(summaryByDate).sort();
    if (dates.length === 0) return [];
    const minDate = parseISO(dates[0]);
    const maxDate = parseISO(dates[dates.length - 1]);
    const allDates = eachDayOfInterval({ start: minDate, end: maxDate }).map(d => format(d, 'yyyy-MM-dd'));

    return allDates.map(date => ({
      date,
      count: summaryByDate[date]?.commits || 0,
      netCodeChange: summaryByDate[date]?.netCodeChange || 0,
    }));
  }, [data]);

  return (
    <div className="bg-card rounded-lg border p-6">
      <div className="mb-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">30-Day Activity Trend</h3>
        </div>
        <FilterBar
          users={users}
          projects={projects}
          metrics={metrics}
          selectedUsers={selectedUsers}
          selectedProjects={selectedProjects}
          selectedMetric={selectedMetric}
          onChangeUsers={onChangeUsers}
          onChangeProjects={onChangeProjects}
          onChangeMetric={onChangeMetric}
          onClear={onClear}
          isLoading={isLoading}
        />
      </div>
      <div className="h-[350px] w-full">
        {isLoading ? (
          <div className="flex items-center justify-center h-full animate-pulse">
            <div className="w-full h-64 bg-muted rounded-lg" />
          </div>
        ) : !chartData || chartData.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <span className="text-gray-400 text-lg">No data</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12 }}
                tickFormatter={(date) =>
                  new Date(date).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                  })
                }
              />
              <YAxis
                tick={{ fontSize: 12, fill: chartType === 'netCodeChange' ? '#ef4444' : undefined }}
                tickFormatter={(value) => value.toLocaleString()}
                domain={chartType === 'netCodeChange' ? ['auto', 'auto'] : [0, (dataMax: number) => Math.ceil(dataMax * 1.1)]}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '0.5rem',
                }}
                labelFormatter={(date) =>
                  new Date(date).toLocaleDateString('en-US', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })
                }
                formatter={(value: any, name: string) => {
                  if (name === 'count') return [value, 'Commits']
                  if (name === 'netCodeChange') return [value, 'Net Code Change']
                  return [value, name]
                }}
              />
              {chartType === 'commit' && (
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="#3b82f6"
                  fillOpacity={1}
                  fill="url(#colorCount)"
                />
              )}
              {chartType === 'netCodeChange' && (
                <Area
                  type="monotone"
                  dataKey="netCodeChange"
                  stroke="#3b82f6"
                  fillOpacity={1}
                  fill="url(#colorCount)"
                  name="Net Code Change"
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
