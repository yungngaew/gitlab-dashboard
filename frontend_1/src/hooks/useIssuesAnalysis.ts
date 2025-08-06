import { useEffect, useState } from 'react';
import { useIssues } from './useIssues';
import { IssueData } from '../services/dashboardApi';

export function useIssuesAnalysis() {
  const { issues, loading } = useIssues();
  // Calculate stats from issues
  const stats = {
    totalOpen: 0,
    criticalHigh: { total: 0, critical: 0, high: 0 },
    overdue: 0,
    projectCount: 0,
  };
  const recommendations: [] = [];

  if (!loading && issues.length > 0) {
    stats.totalOpen = issues.length;
    stats.criticalHigh.critical = issues.filter(i => i.priority === 'critical').length;
    stats.criticalHigh.high = issues.filter(i => i.priority === 'high').length;
    stats.criticalHigh.total = stats.criticalHigh.critical + stats.criticalHigh.high;
    stats.overdue = issues.filter(i => {
      if (!i.due_date) return false;
      const due = new Date(i.due_date);
      const now = new Date();
      return due < now;
    }).length;
    stats.projectCount = new Set(issues.map(i => i.project)).size;
  }

  return { issuesAnalysisData: { stats, recommendations }, loading };
} 