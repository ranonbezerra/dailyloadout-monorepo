import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";

vi.mock("@slate/shared/api", () => ({
	apiFetch: vi.fn(),
}));

import { apiFetch } from "@slate/shared/api";
import {
	banUser,
	clampPlaySession,
	clearConfig,
	demoteGame,
	editGame,
	fetchAdminMe,
	fetchAudit,
	fetchCapture,
	fetchCaptures,
	fetchConfig,
	fetchDashboard,
	fetchGames,
	fetchPick,
	fetchPicks,
	fetchPlaySession,
	fetchPlaySessions,
	fetchUser,
	fetchUsers,
	promoteGame,
	purgeCapture,
	reprocessCapture,
	setConfig,
	unbanUser,
	verifyUser,
} from "./backoffice-api";

const mockApiFetch = apiFetch as Mock;

beforeEach(() => {
	mockApiFetch.mockReset();
	mockApiFetch.mockResolvedValue({});
});

describe("backoffice-api", () => {
	it("fetchAdminMe converts snake_case → camelCase", async () => {
		mockApiFetch.mockResolvedValue({
			public_id: "u1",
			email: "a@b.com",
			display_name: "Admin",
		});
		const me = await fetchAdminMe();
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/me");
		expect(me).toEqual({ publicId: "u1", email: "a@b.com", displayName: "Admin" });
	});

	it("fetchDashboard maps nested recent actions", async () => {
		mockApiFetch.mockResolvedValue({
			users_total: 3,
			users_banned: 1,
			recent_actions: [{ action: "user.ban", target_email: "x@y.com" }],
		});
		const d = await fetchDashboard();
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/dashboard");
		expect(d.usersTotal).toBe(3);
		expect(d.recentActions[0]).toMatchObject({ action: "user.ban", targetEmail: "x@y.com" });
	});

	it("fetchUsers builds the query string from params", async () => {
		mockApiFetch.mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
		await fetchUsers({ q: "joe", banned: true, verified: false, limit: 20, offset: 40 });
		expect(mockApiFetch).toHaveBeenCalledWith(
			"/internal/v1/users?q=joe&banned=true&verified=false&limit=20&offset=40",
		);
	});

	it("fetchUsers omits the query string when no params", async () => {
		mockApiFetch.mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
		await fetchUsers();
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/users");
	});

	it("fetchUser hits the detail path", async () => {
		await fetchUser("abc");
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/users/abc");
	});

	it("banUser POSTs the reason", async () => {
		await banUser("abc", "spam");
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/users/abc/ban", {
			method: "POST",
			body: JSON.stringify({ reason: "spam" }),
		});
	});

	it("banUser sends null reason when omitted", async () => {
		await banUser("abc");
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/users/abc/ban", {
			method: "POST",
			body: JSON.stringify({ reason: null }),
		});
	});

	it("unbanUser and verifyUser POST to their paths", async () => {
		await unbanUser("abc");
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/users/abc/unban", { method: "POST" });
		await verifyUser("abc");
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/users/abc/verify", { method: "POST" });
	});

	it("fetchConfig converts the entries", async () => {
		mockApiFetch.mockResolvedValue({
			items: [{ key: "rate_limit_enabled", effective_value: true, is_overridden: false }],
		});
		const c = await fetchConfig();
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/config");
		expect(c.items[0]).toMatchObject({
			key: "rate_limit_enabled",
			effectiveValue: true,
			isOverridden: false,
		});
	});

	it("setConfig PUTs the value", async () => {
		mockApiFetch.mockResolvedValue({ items: [] });
		await setConfig("cost_user_per_day", 42);
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/config/cost_user_per_day", {
			method: "PUT",
			body: JSON.stringify({ value: 42 }),
		});
	});

	it("clearConfig DELETEs the key", async () => {
		mockApiFetch.mockResolvedValue({ items: [] });
		await clearConfig("cost_user_per_day");
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/config/cost_user_per_day", {
			method: "DELETE",
		});
	});

	it("fetchAudit paginates", async () => {
		mockApiFetch.mockResolvedValue({ items: [], total: 0, limit: 25, offset: 0 });
		await fetchAudit({ limit: 25, offset: 50 });
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/audit?limit=25&offset=50");
	});

	it("fetchGames builds the query string and converts tallies", async () => {
		mockApiFetch.mockResolvedValue({
			items: [{ public_id: "g1", owner_count: 3, is_shared: true }],
			total: 1,
			catalogue_total: 5,
			catalogue_igdb: 4,
			catalogue_manual: 1,
		});
		const r = await fetchGames({ q: "halo", shared: true, source: "igdb", limit: 20, offset: 0 });
		expect(mockApiFetch).toHaveBeenCalledWith(
			"/internal/v1/games?q=halo&shared=true&source=igdb&limit=20&offset=0",
		);
		expect(r.catalogueTotal).toBe(5);
		expect(r.items[0]).toMatchObject({ publicId: "g1", ownerCount: 3, isShared: true });
	});

	it("demoteGame and promoteGame POST to their paths", async () => {
		await demoteGame("g1");
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/games/g1/demote", { method: "POST" });
		await promoteGame("g1");
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/games/g1/promote", { method: "POST" });
	});

	it("editGame PATCHes the changed fields", async () => {
		await editGame("g1", { title: "New Title" });
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/games/g1", {
			method: "PATCH",
			body: JSON.stringify({ title: "New Title" }),
		});
	});

	it("fetchCaptures builds the query string and converts tallies", async () => {
		mockApiFetch.mockResolvedValue({
			items: [{ public_id: "c1", user_email: "a@b.com", candidate_count: 2 }],
			total: 1,
			status_counts: [{ status: "failed", count: 1 }],
		});
		const r = await fetchCaptures({ q: "a@b.com", status: "failed", limit: 20, offset: 0 });
		expect(mockApiFetch).toHaveBeenCalledWith(
			"/internal/v1/captures?q=a%40b.com&status=failed&limit=20&offset=0",
		);
		expect(r.statusCounts[0]).toMatchObject({ status: "failed", count: 1 });
		expect(r.items[0]).toMatchObject({ publicId: "c1", userEmail: "a@b.com", candidateCount: 2 });
	});

	it("fetchCaptures omits the query string when no params", async () => {
		mockApiFetch.mockResolvedValue({ items: [], total: 0, status_counts: [] });
		await fetchCaptures();
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/captures");
	});

	it("fetchCapture hits the detail path", async () => {
		mockApiFetch.mockResolvedValue({ public_id: "c1", candidates: [] });
		await fetchCapture("c1");
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/captures/c1");
	});

	it("reprocessCapture POSTs to the reprocess path", async () => {
		mockApiFetch.mockResolvedValue({ public_id: "c1", candidates: [] });
		await reprocessCapture("c1");
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/captures/c1/reprocess", {
			method: "POST",
		});
	});

	it("purgeCapture DELETEs the capture", async () => {
		await purgeCapture("c1");
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/captures/c1", { method: "DELETE" });
	});

	it("fetchPlaySessions builds the query string and converts tallies", async () => {
		mockApiFetch.mockResolvedValue({
			items: [{ public_id: "m1", user_email: "a@b.com", game_title: "Hades" }],
			total: 1,
			status_counts: [{ status: "active", count: 1 }],
		});
		const r = await fetchPlaySessions({ q: "a@b.com", status: "active", limit: 20, offset: 0 });
		expect(mockApiFetch).toHaveBeenCalledWith(
			"/internal/v1/play-sessions?q=a%40b.com&status=active&limit=20&offset=0",
		);
		expect(r.statusCounts[0]).toMatchObject({ status: "active", count: 1 });
		expect(r.items[0]).toMatchObject({ publicId: "m1", userEmail: "a@b.com", gameTitle: "Hades" });
	});

	it("fetchPlaySessions omits the query string when no params", async () => {
		mockApiFetch.mockResolvedValue({ items: [], total: 0, status_counts: [] });
		await fetchPlaySessions();
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/play-sessions");
	});

	it("fetchPlaySession hits the detail path", async () => {
		mockApiFetch.mockResolvedValue({ public_id: "m1" });
		await fetchPlaySession("m1");
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/play-sessions/m1");
	});

	it("clampPlaySession POSTs to the clamp path", async () => {
		mockApiFetch.mockResolvedValue({ public_id: "m1" });
		await clampPlaySession("m1");
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/play-sessions/m1/clamp", {
			method: "POST",
		});
	});

	it("fetchPicks builds the query string and converts tallies", async () => {
		mockApiFetch.mockResolvedValue({
			items: [{ public_id: "l1", user_email: "a@b.com", available_minutes: 60 }],
			total: 1,
			action_counts: [{ action: "pending", count: 1 }],
		});
		const r = await fetchPicks({ q: "a@b.com", action: "pending", limit: 20, offset: 0 });
		expect(mockApiFetch).toHaveBeenCalledWith(
			"/internal/v1/picks?q=a%40b.com&action=pending&limit=20&offset=0",
		);
		expect(r.actionCounts[0]).toMatchObject({ action: "pending", count: 1 });
		expect(r.items[0]).toMatchObject({
			publicId: "l1",
			userEmail: "a@b.com",
			availableMinutes: 60,
		});
	});

	it("fetchPicks omits the query string when no params", async () => {
		mockApiFetch.mockResolvedValue({ items: [], total: 0, action_counts: [] });
		await fetchPicks();
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/picks");
	});

	it("fetchPick hits the detail path", async () => {
		mockApiFetch.mockResolvedValue({ public_id: "l1" });
		await fetchPick("l1");
		expect(mockApiFetch).toHaveBeenCalledWith("/internal/v1/picks/l1");
	});
});
