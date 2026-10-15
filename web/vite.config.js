import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    server: { port: Number(env.WEB_PORT ?? 5180) },
    test: { include: ["tests/**/*.test.js"] },
  };
});
