import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backend = env.VITE_MCP_PROXY_TARGET ?? "http://127.0.0.1:8000";
  const proxy = Object.fromEntries(
    ["/mcp", "/profile", "/helpers", "/signup", "/signin", "/signout", "/me", "/speak", "/transcribe"].map(
      (path) => [path, { target: backend, changeOrigin: true, ws: path === "/transcribe" }],
    ),
  );
  return {
    server: { host: "127.0.0.1", port: Number(env.WEB_PORT ?? 5180), proxy },
    test: { include: ["tests/**/*.test.js"] },
  };
});
