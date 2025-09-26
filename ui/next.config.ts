import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: {
    // Allow production builds to succeed even if ESLint errors are present
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Allow production builds to succeed even if type errors are present
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
