import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The repo already has its own CLAUDE.md with real project conventions; don't let Next.js
  // regenerate generic AGENTS.md/CLAUDE.md stubs here on every dev-server start.
  agentRules: false,
};

export default nextConfig;
