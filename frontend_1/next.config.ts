import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    turbo: {
      rules: {
        '*.css': {
          loaders: ['css-loader'],
          as: '*.css',
        },
      },
    },
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
        // destination: 'http://10.1.66.74:5000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
