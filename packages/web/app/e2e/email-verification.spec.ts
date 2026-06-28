import { expect, test } from "@playwright/test";
import { setupMockedApp, unverifiedUser } from "./fixtures";

const SHOTS = "e2e/screenshots";

test.describe("Email verification — banner + /verify-email", () => {
	test("unverified users see the verify-email banner and can resend", async ({ page }) => {
		// Override /me to report the account as unverified so the banner shows.
		await setupMockedApp(page, {
			"GET /v1/auth/me": { status: 200, body: unverifiedUser },
		});

		await page.goto("/play");

		const banner = page.getByTestId("verify-email-banner");
		await expect(banner).toBeVisible();
		await expect(banner.getByText("Verify your email", { exact: true })).toBeVisible();

		await page.screenshot({ path: `${SHOTS}/verify-email-banner.png`, fullPage: true });

		// Resend posts to the (mocked) endpoint and surfaces a success toast.
		await banner.getByRole("button", { name: /resend verification/i }).click();
		await expect(page.getByText("Verification email sent")).toBeVisible();

		// The banner can be dismissed for the session.
		await banner.getByRole("button", { name: /dismiss/i }).click();
		await expect(page.getByTestId("verify-email-banner")).toHaveCount(0);
	});

	test("the banner does not show for verified users", async ({ page }) => {
		// Default fixture user is verified.
		await setupMockedApp(page);
		await page.goto("/play");

		await expect(page.getByRole("heading", { name: "Play" })).toBeVisible();
		await expect(page.getByTestId("verify-email-banner")).toHaveCount(0);
	});

	test("/verify-email confirms a valid token and offers a way into the app", async ({ page }) => {
		await setupMockedApp(page, {
			"GET /v1/auth/me": { status: 200, body: unverifiedUser },
			"POST /v1/auth/verify": { status: 200, body: { message: "Email verified" } },
		});

		await page.goto("/verify-email?token=valid-token");

		await expect(page.getByText("Email verified — you're all set.")).toBeVisible();
		const continueLink = page.getByRole("link", { name: /continue to dailyloadout/i });
		await expect(continueLink).toBeVisible();

		await page.screenshot({ path: `${SHOTS}/verify-email-success.png`, fullPage: true });

		await continueLink.click();
		await expect(page).toHaveURL(/\/play/);
	});

	test("/verify-email shows an error for an expired token, with Resend", async ({ page }) => {
		await setupMockedApp(page, {
			"GET /v1/auth/me": { status: 200, body: unverifiedUser },
			"POST /v1/auth/verify": {
				status: 400,
				body: { detail: "Invalid or expired token" },
			},
		});

		await page.goto("/verify-email?token=expired-token");

		await expect(page.getByText(/invalid or has expired/i)).toBeVisible();
		await expect(page.getByRole("button", { name: /resend verification email/i })).toBeVisible();
	});
});
