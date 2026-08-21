import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The repo already has its own CLAUDE.md with real project conventions; don't let Next.js
  // regenerate generic AGENTS.md/CLAUDE.md stubs here on every dev-server start.
  agentRules: false,

  // Deploy as a static export → S3 + CloudFront (spec 007 FR-002, v1.1.0). The dashboard is a pure
  // client SPA, so `next build` emits a static `out/` with no server runtime. `trailingSlash` maps
  // clean URLs to S3 object keys; images are unoptimized because there is no Next image server.
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
