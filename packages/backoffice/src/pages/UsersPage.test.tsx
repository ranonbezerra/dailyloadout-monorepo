import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, type Mock, vi } from "vitest";
import type { AdminUserDetail, AdminUserSummary } from "../types/backoffice";
import { UsersPage } from "./UsersPage";

vi.mock("../hooks/useBackoffice", () => ({
	useUsers: vi.fn(),
	useUser: vi.fn(),
	useUserActions: vi.fn(),
}));
vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

import { useUser, useUserActions, useUsers } from "../hooks/useBackoffice";

const mockUseUsers = useUsers as Mock;
const mockUseUser = useUser as Mock;
const mockUseUserActions = useUserActions as Mock;

function user(over: Partial<AdminUserSummary> = {}): AdminUserSummary {
	return {
		publicId: "u1",
		email: "joe@x.com",
		displayName: "Joe",
		emailVerified: true,
		isBanned: false,
		createdAt: new Date().toISOString(),
		...over,
	};
}

function detail(over: Partial<AdminUserDetail> = {}): AdminUserDetail {
	return {
		...user(),
		avatarUrl: null,
		locale: "en-US",
		timezone: "UTC",
		isAdmin: false,
		hasPassword: true,
		activeSessions: 2,
		...over,
	};
}

function actions() {
	return {
		ban: { mutate: vi.fn(), isPending: false },
		unban: { mutate: vi.fn(), isPending: false },
		verify: { mutate: vi.fn(), isPending: false },
	};
}

interface SetupOpts {
	users?: AdminUserSummary[];
	total?: number;
	isLoading?: boolean;
	isError?: boolean;
	detail?: AdminUserDetail;
}

function setup(opts: SetupOpts = {}) {
	const a = actions();
	mockUseUserActions.mockReturnValue(a);
	mockUseUser.mockReturnValue({ data: opts.detail, isLoading: false });
	mockUseUsers.mockReturnValue({
		data: opts.isError
			? undefined
			: { items: opts.users ?? [user()], total: opts.total ?? 1, limit: 20, offset: 0 },
		isLoading: opts.isLoading ?? false,
		isError: opts.isError ?? false,
	});
	render(
		<MantineProvider>
			<UsersPage />
		</MantineProvider>,
	);
	return a;
}

describe("UsersPage", () => {
	it("renders a user row with email and status", () => {
		setup();
		expect(screen.getByText("joe@x.com")).toBeInTheDocument();
		expect(screen.getByText("active")).toBeInTheDocument();
	});

	it("ban calls the ban mutation", () => {
		const a = setup();
		fireEvent.click(screen.getByLabelText("Ban"));
		expect(a.ban.mutate).toHaveBeenCalledWith({ publicId: "u1" }, expect.anything());
	});

	it("unban calls the unban mutation", () => {
		const a = setup({ users: [user({ isBanned: true })] });
		fireEvent.click(screen.getByLabelText("Unban"));
		expect(a.unban.mutate).toHaveBeenCalledWith("u1", expect.anything());
	});

	it("verify calls the verify mutation", () => {
		const a = setup({ users: [user({ emailVerified: false })] });
		fireEvent.click(screen.getByLabelText("Verify"));
		expect(a.verify.mutate).toHaveBeenCalledWith("u1", expect.anything());
	});

	it("loading and error states render", () => {
		setup({ isLoading: true });
		vi.clearAllMocks();
		setup({ isError: true });
		expect(screen.getByText("Failed to load users.")).toBeInTheDocument();
	});

	it("empty state when no users match", () => {
		setup({ users: [], total: 0 });
		expect(screen.getByText("No users match.")).toBeInTheDocument();
	});

	it("opens the detail drawer with profile + session info", async () => {
		setup({ detail: detail({ activeSessions: 3 }) });
		fireEvent.click(screen.getByText("joe@x.com"));
		expect(await screen.findByText("Active sessions")).toBeInTheDocument();
		expect(screen.getByText("Password")).toBeInTheDocument();
	});

	it("an admin can't be moderated from the detail drawer", async () => {
		setup({ detail: detail({ isAdmin: true }) });
		fireEvent.click(screen.getByText("joe@x.com"));
		expect(await screen.findByText(/Admins can't be moderated/)).toBeInTheDocument();
	});

	it("bans from the detail drawer's action button", async () => {
		const a = setup({ detail: detail({ isAdmin: false }) });
		fireEvent.click(screen.getByText("joe@x.com"));
		const banBtn = await screen.findByRole("button", { name: "Ban user" });
		fireEvent.click(banBtn);
		expect(a.ban.mutate).toHaveBeenCalledWith({ publicId: "u1" }, expect.anything());
	});

	it("verifies from the detail drawer for a banned, unverified user", async () => {
		const a = setup({ detail: detail({ isBanned: true, emailVerified: false }) });
		fireEvent.click(screen.getByText("joe@x.com"));
		fireEvent.click(await screen.findByRole("button", { name: "Verify email" }));
		expect(a.verify.mutate).toHaveBeenCalledWith("u1", expect.anything());
	});

	it("shows pagination when there are more than one page", () => {
		setup({ users: [user()], total: 50 });
		expect(screen.getByText("50 users")).toBeInTheDocument();
	});
});
