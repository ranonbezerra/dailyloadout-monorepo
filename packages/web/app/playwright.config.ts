import { defineConfig, devices } from "@playwright/test";

// E2E config. Tests run against the Vite dev server with the API mocked at the
// network layer (see e2e/fixtures.ts), so the full backend isn't required —
// deterministic, fast, and ideal for driving real UI flows + UX screenshots.
export default defineConfig({
	testDir: "./e2e",
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 1 : 0,
	reporter: process.env.CI ? "github" : [["list"], ["html", { open: "never" }]],
	use: {
		baseURL: "http://localhost:4321",
		trace: "on-first-retry",
		screenshot: "only-on-failure",
	},
	projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
	webServer: {
		command: "bunx vite --port 4321 --strictPort",
		url: "http://localhost:4321",
		reuseExistingServer: !process.env.CI,
		timeout: 60_000,
	},
});
