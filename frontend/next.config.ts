import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // docs/SECURITY.md §41/§71: restrict browser capabilities to what this
  // app actually uses. Camera/geolocation are needed (face capture,
  // location verification); everything else Permissions-Policy covers by
  // default is denied. The backend sets its own equivalent headers for its
  // JSON responses (see backend/app/core/security_headers.py) — these two
  // are separate response surfaces, not one shared config.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(self), geolocation=(self)" },
        ],
      },
    ];
  },
};

export default nextConfig;
