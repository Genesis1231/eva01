/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  webpack(config) {
    return config;
  },
  // Prevent pre-rendering errors by rendering certain pages only on client side
  experimental: {
    // Prevent issues with browser-only APIs during static generation
    esmExternals: 'loose',
  },
};

module.exports = nextConfig; 