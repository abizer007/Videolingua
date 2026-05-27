import type { Metadata } from 'next'
import { Outfit } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'

const outfit = Outfit({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'VidioLingua - AI-Powered Multilingual Video Localization',
  description: 'Translate any video. Speak every language. Advanced AI pipeline for video localization.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={outfit.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
