import type { Page, Route } from "@playwright/test";

// ---------------------------------------------------------------------------
// E2E fixtures: mock the API at the network layer so flows run deterministically
// without a live backend. The access token now lives in memory and the refresh
// token is an httpOnly cookie (unseedable from JS), so we authenticate by
// mocking POST /v1/auth/refresh — the app's bootstrap silent-refresh restores
// the session on load. Tests can pass `overrides` keyed by "METHOD /path" to
// swap in scenario-specific responses.
// ---------------------------------------------------------------------------

const NOW = "2026-01-01T00:00:00Z";

const user = {
	id: 1,
	public_id: "11111111-1111-1111-1111-111111111111",
	email: "demo@dailyloadout.dev",
	display_name: "Demo Player",
	email_verified: true,
	locale: "en",
	timezone: "UTC",
	created_at: NOW,
	updated_at: NOW,
};

/** Same user but still unverified — drives the "Verify your email" banner. */
export const unverifiedUser = { ...user, email_verified: false };

const platform = { id: 1, slug: "pc", label: "PC", family: "computer" };
const switchPlatform = { id: 2, slug: "switch", label: "Nintendo Switch", family: "console" };

function game(slug: string, title: string) {
	return {
		public_id: `g-${slug}`,
		slug,
		title,
		cover_url: null,
		summary: null,
		genres: ["action", "metroidvania"],
		metadata_source: "igdb",
		first_release_date: null,
		created_at: NOW,
	};
}

function platformState(slug: string, status: string, plat = platform) {
	return {
		public_id: `le-${slug}-${plat.slug}`,
		platform: plat,
		status,
		notes: null,
		acquired_at: null,
		last_played_at: null,
		mission_next_action: null,
		created_at: NOW,
		updated_at: NOW,
	};
}

/** A grouped library game: one game, one or more per-platform states. */
function group(slug: string, title: string, platforms: ReturnType<typeof platformState>[]) {
	return {
		game: game(slug, title),
		platforms,
	};
}

type Canned = { status: number; body: unknown };

export const DEFAULT_ROUTES: Record<string, Canned> = {
	"GET /v1/auth/me": { status: 200, body: user },
	// Bootstrap silent-refresh: the access token is in memory (lost on reload),
	// so the app restores the session via the cookie-backed refresh on load.
	"POST /v1/auth/refresh": {
		status: 200,
		body: { access_token: "e2e-access-token", refresh_token: "" },
	},
	"POST /v1/auth/verify": { status: 200, body: { message: "Email verified" } },
	"POST /v1/auth/resend-verification": {
		status: 200,
		body: { message: "Verification email sent" },
	},
	"GET /v1/library": {
		status: 200,
		body: {
			// Grouped: one row per distinct game. Hollow Knight is owned on two
			// platforms, so it appears once with two per-platform states.
			items: [
				group("hollow-knight", "Hollow Knight", [
					platformState("hollow-knight", "playing", platform),
					platformState("hollow-knight", "backlog", switchPlatform),
				]),
				group("hades", "Hades", [platformState("hades", "backlog", platform)]),
				group("celeste", "Celeste", [platformState("celeste", "completed", platform)]),
			],
			total: 3,
			limit: 50,
			offset: 0,
		},
	},
	"GET /v1/platforms": {
		status: 200,
		body: [platform, switchPlatform],
	},
	"GET /v1/games/genres": { status: 200, body: ["action", "metroidvania", "roguelike"] },
	"GET /v1/missions/active": { status: 404, body: { detail: "No active mission" } },
	"GET /v1/missions": { status: 200, body: { items: [], total: 0, limit: 20, offset: 0 } },
	"GET /v1/captures": { status: 200, body: { items: [], total: 0, limit: 20, offset: 0 } },
	"GET /v1/stats/overview": {
		status: 200,
		body: {
			total_games: 3,
			status_counts: { playing: 1, backlog: 1, completed: 1 },
			missions_last_30d: 5,
			avg_mission_duration_minutes: 47,
			user_created_at: NOW,
		},
	},
	"GET /v1/stats/play-heatmap": {
		status: 200,
		body: { days: [{ date: "2026-06-01", count: 2, total_minutes: 90 }] },
	},
	"GET /v1/stats/genres": {
		status: 200,
		body: { genres: [{ genre: "action", total_minutes: 120, mission_count: 3 }] },
	},
	"GET /v1/stats/platforms": {
		status: 200,
		body: {
			platforms: [
				{
					platform_slug: "pc",
					platform_label: "PC",
					game_count: 2,
					mission_count: 3,
					total_minutes: 120,
				},
			],
		},
	},
	"GET /v1/stats/timeline": { status: 200, body: { items: [], total: 0 } },
	"GET /v1/loadouts": { status: 200, body: { items: [], total: 0, limit: 20, offset: 0 } },
};

// A small SSE stream for the concierge chat endpoint.
const CONCIERGE_SSE = [
	'data: {"tool": "search_library", "phase": "start"}',
	'data: {"tool": "search_library", "phase": "end"}',
	'data: {"token": "Give Hollow Knight a go tonight."}',
	'data: {"recommendation": {"id": "le-hollow-knight", "title": "Hollow Knight"}}',
	'data: {"done": true, "thread_id": "t-e2e"}',
]
	.map((l) => `${l}\n\n`)
	.join("");

export async function setupMockedApp(
	page: Page,
	overrides: Record<string, Canned> = {},
): Promise<void> {
	await page.route("**/v1/**", async (route: Route) => {
		const req = route.request();
		const url = new URL(req.url());
		const key = `${req.method()} ${url.pathname}`;

		if (req.method() === "POST" && url.pathname === "/v1/concierge/chat") {
			await route.fulfill({
				status: 200,
				headers: { "content-type": "text/event-stream" },
				body: CONCIERGE_SSE,
			});
			return;
		}

		const canned = overrides[key] ?? DEFAULT_ROUTES[key];
		if (canned) {
			await route.fulfill({
				status: canned.status,
				contentType: "application/json",
				body: JSON.stringify(canned.body),
			});
			return;
		}
		// Unknown endpoints: succeed quietly so a missing mock never hangs a test.
		await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
	});
}
