/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  compress: true,
  poweredByHeader: false,
  output: "standalone",
  experimental: {
    workerThreads: true,
  },
};

export default nextConfig;
