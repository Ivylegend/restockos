import type { NextConfig } from 'next';

const config: NextConfig = {
  poweredByHeader: false,
  async rewrites() {
    const upstream = process.env.INTERNAL_API_URL;
    return upstream ? [{ source: '/api/:path*', destination: upstream + '/:path*' }] : [];
  },
};

export default config;
