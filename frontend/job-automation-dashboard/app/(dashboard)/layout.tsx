import type React from "react"
import { SidebarNav } from "@/components/sidebar-nav"
import { ProtectedRoute } from "@/components/protected-route"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ProtectedRoute>
      <div className="flex min-h-screen">
        <SidebarNav />
        <main className="flex-1 pl-64">
          <div className="container py-8">{children}</div>
        </main>
      </div>
    </ProtectedRoute>
  )
}
