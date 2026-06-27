import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, type Mock, vi } from "vitest";
import type { AdminUserSummary } from "../../types/backoffice";
import { UsersPage } from "./UsersPage";

vi.mock("../../hooks/useBackoffice", () => ({
	useUsers: vi.fn(),
	useUser: vi.fn(),
	useUserActions: vi.fn(),
}));
vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

import { useUser, useUserActions, useUsers } from "../../hooks/useBackoffice";

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

function renderPage() {
	return render(
		<MantineProvider>
			<UsersPage />
		</MantineProvider>,
	);
}

describe("UsersPage", () => {
	const actions = () => ({
		ban: { mutate: vi.fn(), isPending: false },
		unban: { mutate: vi.fn(), isPending: false },
		verify: { mutate: vi.fn(), isPending: false },
	});

	it("renders a user row with email and status", () => {
		mockUseUserActions.mockReturnValue(actions());
		mockUseUser.mockReturnValue({ data: undefined, isLoading: false });
		mockUseUsers.mockReturnValue({
			data: { items: [user()], total: 1, limit: 20, offset: 0 },
			isLoading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getByText("joe@x.com")).toBeInTheDocument();
		expect(screen.getByText("active")).toBeInTheDocument();
	});

	it("clicking ban calls the ban mutation", () => {
		const a = actions();
		mockUseUserActions.mockReturnValue(a);
		mockUseUser.mockReturnValue({ data: undefined, isLoading: false });
		mockUseUsers.mockReturnValue({
			data: { items: [user()], total: 1, limit: 20, offset: 0 },
			isLoading: false,
			isError: false,
		});
		renderPage();
		fireEvent.click(screen.getByLabelText("Ban"));
		expect(a.ban.mutate).toHaveBeenCalledWith({ publicId: "u1" }, expect.anything());
	});

	it("shows an empty state when no users match", () => {
		mockUseUserActions.mockReturnValue(actions());
		mockUseUser.mockReturnValue({ data: undefined, isLoading: false });
		mockUseUsers.mockReturnValue({
			data: { items: [], total: 0, limit: 20, offset: 0 },
			isLoading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getByText("No users match.")).toBeInTheDocument();
	});
});
