import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // Fait passer les appels du navigateur par Next.js pour garder une origine unique.
  async rewrites() {
    const apiOrigin = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
  },
};

export default nextConfig;
