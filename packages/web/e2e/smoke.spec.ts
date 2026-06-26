import { expect, test } from "@playwright/test";
import { setupMockedApp } from "./fixtures";

const SHOTS = "e2e/screenshots";

test.describe("DailyLoadout web — smoke + UX capture", () => {
	test("redirects unauthenticated users to login", async ({ page }) => {
		// No token seeded and every call 401 → the guard should bounce to /login.
		await page.route("**/v1/**", (r) =>
			r.fulfill({
				status: 401,
				contentType: "application/json",
				body: '{"detail":"unauthorized"}',
			}),
		);
		await page.goto("/play");
		await expect(page).toHaveURL(/\/login/);
		await page.screenshot({ path: `${SHOTS}/login.png`, fullPage: true });
	});

	test("play hub shows the three start doors", async ({ page }) => {
		await setupMockedApp(page);
		await page.goto("/play");
		await expect(page.getByRole("heading", { name: "Play" })).toBeVisible();
		await expect(page.getByText("What's the move?")).toBeVisible();
		await expect(page.getByText("I'll choose")).toBeVisible();
		await page.screenshot({ path: `${SHOTS}/play-hub.png`, fullPage: true });
	});

	test("library lists grouped games with per-platform badges", async ({ page }) => {
		await setupMockedApp(page);
		await page.goto("/library");
		await expect(page.getByRole("heading", { name: "Library" })).toBeVisible();

		// Grouped shape: Hollow Knight is owned on two platforms but renders as a
		// SINGLE row — its title appears exactly once in the table.
		await expect(page.getByText("Hollow Knight", { exact: true })).toHaveCount(1);

		// Each platform shows its own status badge within that one row.
		await expect(page.getByText("PC: playing")).toBeVisible();
		await expect(page.getByText("Nintendo Switch: backlog")).toBeVisible();

		await page.screenshot({ path: `${SHOTS}/library.png`, fullPage: true });
	});

	test("analytics dashboard renders", async ({ page }) => {
		await setupMockedApp(page);
		await page.goto("/analytics");
		await expect(page.getByRole("heading", { name: "Analytics" })).toBeVisible();
		await page.waitForLoadState("networkidle");
		await page.screenshot({ path: `${SHOTS}/analytics.png`, fullPage: true });
	});

	test("loadout shows the questionnaire", async ({ page }) => {
		await setupMockedApp(page);
		await page.goto("/play/loadout");
		await expect(page.getByRole("button", { name: /Roll the dice/i })).toBeVisible();
		await page.screenshot({ path: `${SHOTS}/loadout.png`, fullPage: true });
	});

	test("mobile nav opens via the burger and exposes IGDB attribution", async ({ page }) => {
		await page.setViewportSize({ width: 390, height: 844 }); // iPhone-ish
		await setupMockedApp(page);
		await page.goto("/play");

		// Navbar (and its IGDB credit) starts collapsed on phones.
		const burger = page.getByRole("button", { name: /toggle navigation/i });
		await expect(burger).toBeVisible();

		await burger.click();
		const credit = page.getByRole("link", { name: /igdb\.com/i });
		await expect(credit).toBeVisible();

		// Tapping a nav item navigates and closes the navbar.
		await page.getByText("Library", { exact: true }).click();
		await expect(page).toHaveURL(/\/library/);
	});

	test("concierge streams a reply and offers a Play CTA", async ({ page }) => {
		await setupMockedApp(page);
		await page.goto("/play/concierge");
		await expect(page.getByText("What should you play tonight?")).toBeVisible();

		await page.getByPlaceholder("Ask the concierge…").fill("what should I play?");
		await page.keyboard.press("Enter");

		// Streamed prose + the validated recommendation CTA (marker withheld).
		await expect(page.getByText(/Give Hollow Knight a go/)).toBeVisible();
		await expect(page.getByRole("button", { name: /Play Hollow Knight/ })).toBeVisible();
		await page.screenshot({ path: `${SHOTS}/concierge.png`, fullPage: true });
	});
});
