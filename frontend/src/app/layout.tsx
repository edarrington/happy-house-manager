import type { Metadata } from 'next'
import './globals.css'
import Sidebar from '@/components/Sidebar'
import Providers from './providers'

export const metadata: Metadata = {
  title: 'Happy House Manager',
  description: 'Home management app for the Darrington family',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 flex flex-col overflow-hidden">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  )
}
