/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: ['localhost'],
  },
  webpack: (config, { dev }) => {
    if (dev) {
      // Avoid filesystem cache warnings on some Windows setups.
      config.cache = false
    }
    return config
  },
}

module.exports = nextConfig
