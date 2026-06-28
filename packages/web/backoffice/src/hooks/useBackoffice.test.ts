import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { createWrapper } from "../test/wrapper";

vi.mock("../lib/backoffice-api", () => ({
	fetchAdminMe: vi.fn(),
	fetchDashboard: vi.fn(),
	fetchUsers: vi.fn(),
	fetchUser: vi.fn(),
	fetchConfig: vi.fn(),
	fetchAudit: vi.fn(),
	fetchGames: vi.fn(),
	banUser: vi.fn(),
	unbanUser: vi.fn(),
	verifyUser: vi.fn(),
	setConfig: vi.fn(),
	clearConfig: vi.fn(),
	demoteGame: vi.fn(),
	promoteGame: vi.fn(),
	editGame: vi.fn(),
}));

import * as api from "../lib/backoffice-api";
import {
	useAdminMe,
	useAudit,
	useConfigActions,
	useDashboard,
	useGameActions,
	useGames,
	useUser,
	useUserActions,
	useUsers,
} from "./useBackoffice";

beforeEach(() => {
	vi.clearAllMocks();
});

describe("useBackoffice queries", () => {
	it("useAdminMe / useDashboard / useConfig / useAudit call their fetchers", async () => {
		(api.fetchAdminMe as Mock).mockResolvedValue({ email: "a@b.com" });
		(api.fetchDashboard as Mock).mockResolvedValue({ usersTotal: 1 });
		(api.fetchAudit as Mock).mockResolvedValue({ items: [] });

		const wrapper = createWrapper();
		const me = renderHook(() => useAdminMe(), { wrapper });
		const dash = renderHook(() => useDashboard(), { wrapper });
		const audit = renderHook(() => useAudit({ limit: 25, offset: 0 }), { wrapper });

		await waitFor(() => expect(me.result.current.isSuccess).toBe(true));
		await waitFor(() => expect(dash.result.current.isSuccess).toBe(true));
		await waitFor(() => expect(audit.result.current.isSuccess).toBe(true));
		expect(api.fetchAdminMe).toHaveBeenCalled();
		expect(api.fetchDashboard).toHaveBeenCalled();
		expect(api.fetchAudit).toHaveBeenCalledWith({ limit: 25, offset: 0 });
	});

	it("useUsers / useGames pass params; useUser is disabled when id is null", async () => {
		(api.fetchUsers as Mock).mockResolvedValue({ items: [] });
		(api.fetchGames as Mock).mockResolvedValue({ items: [] });
		const wrapper = createWrapper();

		renderHook(() => useUsers({ q: "joe" }), { wrapper });
		renderHook(() => useGames({ source: "igdb" }), { wrapper });
		const u = renderHook(() => useUser(null), { wrapper });

		await waitFor(() => expect(api.fetchUsers).toHaveBeenCalledWith({ q: "joe" }));
		expect(api.fetchGames).toHaveBeenCalledWith({ source: "igdb" });
		// disabled query never fetches
		expect(api.fetchUser).not.toHaveBeenCalled();
		expect(u.result.current.fetchStatus).toBe("idle");
	});
});

describe("useBackoffice mutations", () => {
	it("user actions resolve and call the API", async () => {
		(api.banUser as Mock).mockResolvedValue({});
		(api.verifyUser as Mock).mockResolvedValue({});
		const { result } = renderHook(() => useUserActions(), { wrapper: createWrapper() });

		await result.current.ban.mutateAsync({ publicId: "u1", reason: "x" });
		await result.current.verify.mutateAsync("u1");
		expect(api.banUser).toHaveBeenCalledWith("u1", "x");
		expect(api.verifyUser).toHaveBeenCalledWith("u1");
	});

	it("config + game actions resolve and call the API", async () => {
		(api.setConfig as Mock).mockResolvedValue({ items: [] });
		(api.demoteGame as Mock).mockResolvedValue({});
		(api.editGame as Mock).mockResolvedValue({});
		const cfg = renderHook(() => useConfigActions(), { wrapper: createWrapper() });
		const games = renderHook(() => useGameActions(), { wrapper: createWrapper() });

		await cfg.result.current.set.mutateAsync({ key: "rate_limit_enabled", value: true });
		await games.result.current.demote.mutateAsync("g1");
		await games.result.current.edit.mutateAsync({ publicId: "g1", edit: { title: "T" } });
		expect(api.setConfig).toHaveBeenCalledWith("rate_limit_enabled", true);
		expect(api.demoteGame).toHaveBeenCalledWith("g1");
		expect(api.editGame).toHaveBeenCalledWith("g1", { title: "T" });
	});
});
