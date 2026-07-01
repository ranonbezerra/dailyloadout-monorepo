import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
// @ts-expect-error — plain .mjs helper shared by both web apps (no types needed)
import { cspPlugin, originOf } from "../csp.mjs";

// Distinct dev port from the player app (web runs on 5173) so both can run side
// by side against the same API.
export default defineConfig(({ mode }) => {
	const env = loadEnv(mode, process.cwd(), "");
	return {
		plugins: [
			react(),
			// Build-only CSP; backoffice has no Turnstile so Cloudflare stays disallowed.
			cspPlugin({ apiOrigin: originOf(env.VITE_API_URL), allowCloudflare: false }),
		],
		server: { port: 5174 },
	};
});
