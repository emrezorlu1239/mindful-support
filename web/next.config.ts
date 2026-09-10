import type { NextConfig } from 'next';

const nextConfig: NextConfig = process.env.MINDFUL_STATIC_EXPORT === '1' ? { output: 'export' } : {};

export default nextConfig;
