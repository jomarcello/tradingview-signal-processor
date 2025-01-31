'use client'

import { Home, ShoppingBag, Calendar, FileText, PieChart, Users } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'

const navItems = [
  { icon: Home, label: 'Home', href: '/home' },
  { icon: ShoppingBag, label: 'Orders', href: '/orders' },
  { icon: Calendar, label: 'Kalender', href: '/calendar' },
  { icon: FileText, label: 'Documenten', href: '/documents' },
  { icon: PieChart, label: 'Rapporten', href: '/reports' },
  { icon: Users, label: 'Gebruikers', href: '/users' },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-20 bg-white border-r border-gray-200 flex flex-col items-center py-4">
      {navItems.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={cn(
            "p-3 rounded-lg mb-2 hover:bg-gray-100",
            pathname === item.href ? "bg-gray-100" : ""
          )}
        >
          <item.icon className="w-6 h-6 text-gray-600" />
        </Link>
      ))}
    </aside>
  )
} 