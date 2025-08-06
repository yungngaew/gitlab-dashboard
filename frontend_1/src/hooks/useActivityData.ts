import { useState, useEffect } from 'react'
import { fetchActivityData, fetchActivityDetailData, ActivitySummaryData, ActivityDetailData } from '../services/dashboardApi'

export function useActivityData() {
  const [data, setData] = useState<ActivitySummaryData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true)
        setError(null)
        const activityData = await fetchActivityData()
        setData(activityData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load activity data')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  return { data, loading, error }
}

export function useActivityDetailData(
  options: {
    userIds?: number[]
    projectIds?: number[]
    days?: number
  } = {}
) {
  const [data, setData] = useState<ActivityDetailData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true)
        setError(null)
        const activityDetailData = await fetchActivityDetailData(options)
        setData(activityDetailData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load activity detail data')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [options.userIds, options.projectIds, options.days])

  return { data, loading, error }
} 