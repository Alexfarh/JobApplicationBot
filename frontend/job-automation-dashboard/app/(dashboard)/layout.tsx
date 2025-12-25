import type React from "react"
import { SidebarNav } from "@/components/sidebar-nav"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen">
      <SidebarNav />
      <main className="flex-1 pl-64">
        <div className="container py-8">{children}</div>
      </main>
    </div>
  )
}
