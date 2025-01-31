'use client'

import { Inter } from 'next/font/google'
import Sidebar from '@/components/layout/Sidebar'
import Header from '@/components/layout/Header'
import { cn } from '@/lib/utils'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="nl">
      <body className={cn(inter.className, "bg-gray-50")}>
        <div className="flex h-screen">
          <Sidebar />
          <div className="flex-1 flex flex-col overflow-hidden">
            <Header />
            <main className="flex-1 overflow-y-auto p-4">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  )
} 