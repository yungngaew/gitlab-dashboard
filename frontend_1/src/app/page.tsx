'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    // Redirect to dashboard after 2 seconds
    const timeout = setTimeout(() => {
      router.push('/dashboard')
    }, 2000)

    return () => clearTimeout(timeout)
  }, [router])

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-8">
      <main className="max-w-2xl mx-auto text-center space-y-6">
        <div className="space-y-4">
          <h1 className="text-4xl font-bold tracking-tight">
            GitLab Analytics Dashboard
          </h1>
          <p className="text-xl text-muted-foreground">
            Comprehensive insights into your GitLab development workflow
          </p>
        </div>

        <div className="animate-pulse text-sm text-muted-foreground">
          Redirecting to dashboard...
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
          <div className="p-6 bg-card rounded-lg border text-center">
            <h3 className="font-semibold mb-2">Project Analytics</h3>
            <p className="text-sm text-muted-foreground">
              Track project health and activity metrics
            </p>
          </div>

          <div className="p-6 bg-card rounded-lg border text-center">
            <h3 className="font-semibold mb-2">Team Insights</h3>
            <p className="text-sm text-muted-foreground">
              Monitor team performance and collaboration
            </p>
          </div>

          <div className="p-6 bg-card rounded-lg border text-center">
            <h3 className="font-semibold mb-2">Issue Tracking</h3>
            <p className="text-sm text-muted-foreground">
              Analyze issue resolution and trends
            </p>
          </div>
        </div>
      </main>

      <footer className="fixed bottom-0 w-full p-6 border-t bg-background/80 backdrop-blur-sm">
        <div className="container mx-auto flex justify-between items-center text-sm text-muted-foreground">
          <p>GitLab Analytics Dashboard</p>
          <p>© {new Date().getFullYear()} All rights reserved</p>
        </div>
      </footer>
    </div>
  )
}
