import React, { useState } from 'react'

export interface WorkloadRow {
  author_name: string
  open: number | null
  inProgress: number | null
  total: number | null
}

interface WorkloadTableProps {
  data: WorkloadRow[]
  loading?: boolean
}

export const WorkloadTable: React.FC<WorkloadTableProps> = ({ data, loading }) => {
  const [sortBy, setSortBy] = useState<'open' | 'inProgress' | 'total'>('total');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  function handleSort(col: 'open' | 'inProgress' | 'total') {
    if (sortBy === col) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(col);
      setSortDir('desc');
    }
  }

  const sortedData = React.useMemo(() => {
    if (!data) return [];
    const arr = [...data];
    arr.sort((a, b) => {
      const aVal = a[sortBy] ?? 0;
      const bVal = b[sortBy] ?? 0;
      if (sortDir === 'asc') return aVal - bVal;
      return bVal - aVal;
    });
    return arr;
  }, [data, sortBy, sortDir]);

  const sortArrow = (col: 'open' | 'inProgress' | 'total') =>
    sortBy === col ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '';

  return (
    <div className="w-full overflow-x-auto">
      <table className="min-w-full rounded-lg text-sm md:text-base bg-background">
        <thead className="sticky top-0 bg-background z-10">
          <tr>
            <th className="px-2 md:px-4 py-2 text-left whitespace-nowrap font-bold">Name</th>
            <th className="px-2 md:px-4 py-2 text-right whitespace-nowrap font-bold cursor-pointer select-none" onClick={() => handleSort('open')}>Opened{sortArrow('open')}</th>
            <th className="px-2 md:px-4 py-2 text-right whitespace-nowrap font-bold cursor-pointer select-none" onClick={() => handleSort('inProgress')}>In Progress{sortArrow('inProgress')}</th>
            <th className="px-2 md:px-4 py-2 text-right whitespace-nowrap font-bold cursor-pointer select-none" onClick={() => handleSort('total')}>Total{sortArrow('total')}</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr><td colSpan={4} className="text-center py-8">Loading...</td></tr>
          ) : data.length === 0 ? (
            <tr><td colSpan={4} className="text-center py-8">-</td></tr>
          ) : (
            sortedData.map((row, idx) => (
              <tr key={row.author_name + idx}>
                <td className="px-2 md:px-4 py-2 font-medium whitespace-nowrap">{row.author_name || '-'}</td>
                <td className="px-2 md:px-4 py-2 text-right whitespace-nowrap">{row.open === null || row.open === undefined ? '-' : row.open}</td>
                <td className="px-2 md:px-4 py-2 text-right whitespace-nowrap">{row.inProgress === null || row.inProgress === undefined ? '-' : row.inProgress}</td>
                <td className="px-2 md:px-4 py-2 text-right whitespace-nowrap">{row.total === null || row.total === undefined ? '-' : row.total}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
} 