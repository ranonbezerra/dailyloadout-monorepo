/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [react()],
	test: {
		globals: true,
		environment: "jsdom",
		setupFiles: "./src/test/setup.ts",
		include: ["src/**/*.test.{ts,tsx}"],
		coverage: {
			provider: "v8",
			include: ["src/**/*.{ts,tsx}"],
			// Exclude app bootstrap, type-only ambient files, and test helpers —
			// non-logic that shouldn't count toward the coverage bar.
			exclude: ["src/main.tsx", "src/theme.ts", "src/vite-env.d.ts", "src/test/**"],
			// Match the API gate's line-coverage bar so all packages hold ≥90%.
			thresholds: { lines: 90 },
		},
	},
});
