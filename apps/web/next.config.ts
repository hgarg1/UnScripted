import path from "node:path";

const nextConfig = {
  transpilePackages: ["@unscripted/contracts", "@unscripted/ui"],
  typedRoutes: true,
  outputFileTracingRoot: path.join(__dirname, "../.."),
};

export default nextConfig;
