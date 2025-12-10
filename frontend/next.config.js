/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  // Désactiver le cache turbo pour éviter les problèmes de manifest
  // experimental: {
  //   turbo: false,  // Removed - invalid config option
  // },
  // Augmenter les timeouts pour éviter les erreurs de chunks
  onDemandEntries: {
    maxInactiveAge: 60 * 1000, // 60 secondes
    pagesBufferLength: 5,
  },
}

module.exports = nextConfig

