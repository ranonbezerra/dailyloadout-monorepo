import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
// @ts-expect-error — plain .mjs helper shared by both web apps (no types needed)
import { cspPlugin, originOf } from "../csp.mjs";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
	const env = loadEnv(mode, process.cwd(), "");
	return {
		plugins: [
			react(),
			// Build-only CSP; connect-src tracks the API origin this build targets.
			cspPlugin({ apiOrigin: originOf(env.VITE_API_URL), allowCloudflare: true }),
		],
	};
});
