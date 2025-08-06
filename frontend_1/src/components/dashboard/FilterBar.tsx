import React, { useState, useRef, useEffect } from 'react';

export interface FilterBarProps {
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

// Custom Autocomplete Dropdown (single/multi)
export function AutocompleteDropdown({
  options,
  selected,
  onChange,
  placeholder,
  label,
  isLoading,
  multi = true,
  className = '',
}: {
  options: { id: number; name: string }[];
  selected: number[];
  onChange: (ids: number[]) => void;
  placeholder: string;
  label: string;
  isLoading?: boolean;
  multi?: boolean;
  className?: string;
}) {
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  const filtered = options.filter(o => o.name.toLowerCase().includes(search.toLowerCase()));

  function toggleSelect(id: number) {
    if (multi) {
      if (selected.includes(id)) onChange(selected.filter(s => s !== id));
      else onChange([...selected, id]);
    } else {
      onChange([id]);
      setOpen(false);
    }
  }

  return (
    <div className={`relative ${className}`} ref={ref}>
      <label className="block text-xs mb-1">{label}</label>
      <div
        className={`border rounded h-11 px-4 text-sm bg-white flex items-center cursor-pointer ${isLoading ? 'opacity-60' : ''}`}
        onClick={() => !isLoading && setOpen(v => !v)}
        tabIndex={0}
      >
        <span className="flex-1 text-left text-gray-700 truncate">
          {selected.length === 0 ? (
            <span className="text-gray-400">{placeholder}</span>
          ) : (
            options.filter(o => selected.includes(o.id)).map(o => o.name).join(', ')
          )}
        </span>
        <svg className="w-4 h-4 ml-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
      </div>
      {open && (
        <div className="absolute z-10 bg-white border rounded shadow w-full mt-1 max-h-48 overflow-auto">
          <input
            className="w-full px-2 py-1 border-b text-xs focus:outline-none"
            placeholder={placeholder}
            value={search}
            onChange={e => setSearch(e.target.value)}
            autoFocus
          />
          {filtered.length === 0 && (
            <div className="px-2 py-2 text-xs text-gray-400">No results</div>
          )}
          {filtered.map(opt => (
            <div
              key={opt.id}
              className={`px-2 py-2 text-sm cursor-pointer hover:bg-blue-50 flex items-center ${selected.includes(opt.id) ? 'bg-blue-100 font-semibold' : ''}`}
              onClick={() => toggleSelect(opt.id)}
            >
              {multi && (
                <input type="checkbox" checked={selected.includes(opt.id)} readOnly className="mr-2" />
              )}
              {opt.name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export const FilterBar: React.FC<FilterBarProps> = ({
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
}) => {
  return (
    <div className="flex flex-wrap items-center gap-4 mb-4 w-full">
      {/* User Filter */}
      <AutocompleteDropdown
        options={users}
        selected={selectedUsers}
        onChange={onChangeUsers}
        placeholder="Select user(s)..."
        label="User"
        isLoading={isLoading}
        multi={true}
      />
      {/* Project Filter */}
      <AutocompleteDropdown
        options={projects}
        selected={selectedProjects}
        onChange={onChangeProjects}
        placeholder="Select project(s)..."
        label="Project"
        isLoading={isLoading}
        multi={true}
      />
      {/* Metric Dropdown */}
      <div className="min-w-[140px]">
        <label className="block text-xs mb-1">Metric</label>
        <select
          className="border rounded px-2 py-2 text-sm w-full"
          value={selectedMetric}
          onChange={e => onChangeMetric(e.target.value)}
          disabled={isLoading}
        >
          {metrics.map(m => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
      </div>
      {/* Clear Filter Button */}
      <button
        className="ml-auto px-3 py-2 text-xs border rounded bg-white hover:bg-gray-100"
        onClick={onClear}
        disabled={isLoading}
        type="button"
      >
        Clear Filter
      </button>
    </div>
  );
}; 