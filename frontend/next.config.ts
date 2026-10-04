import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Hide the dev-only Next.js indicator. It sits bottom-left over the app's
  // own footer bar and lands in every screenshot; it never ships in a build.
  devIndicators: false,
};

export default nextConfig;
