import type { Metadata } from 'next'
import './globals.css'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'ESILV Smart Assistant',
  description: 'Intelligent chatbot for ESILV engineering school',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <Link href="/" className="text-xl font-bold text-primary-600">
                  ESILV Smart Assistant
                </Link>
              </div>
              <div className="flex items-center space-x-4">
                <Link href="/" className="text-gray-700 hover:text-primary-600">
                  Chat
                </Link>
                <Link href="/rag" className="text-gray-700 hover:text-primary-600">
                  RAG
                </Link>
                <Link href="/admin" className="text-gray-700 hover:text-primary-600">
                  Admin
                </Link>
              </div>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  )
}

