import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, type Mock, vi } from "vitest";
import type { DashboardSummary } from "../types/backoffice";
import { DashboardPage } from "./DashboardPage";

vi.mock("../hooks/useBackoffice", () => ({
	useDashboard: vi.fn(),
}));

import { useDashboard } from "../hooks/useBackoffice";

const mockUseDashboard = useDashboard as Mock;

function renderPage() {
	return render(
		<MantineProvider>
			<DashboardPage />
		</MantineProvider>,
	);
}

const summary: DashboardSummary = {
	usersTotal: 42,
	usersBanned: 3,
	usersUnverified: 7,
	admins: 2,
	missionsActive: 5,
	catalogueSize: 128,
	configOverrides: 1,
	recentActions: [
		{
			action: "user.ban",
			detail: "spam",
			createdAt: new Date().toISOString(),
			adminPublicId: "a1",
			adminEmail: "boss@x.com",
			targetPublicId: "u1",
			targetEmail: "bad@x.com",
		},
	],
};

describe("DashboardPage", () => {
	it("renders the metric values", () => {
		mockUseDashboard.mockReturnValue({ data: summary, isLoading: false, isError: false });
		renderPage();
		expect(screen.getByText("42")).toBeInTheDocument();
		expect(screen.getByText("128")).toBeInTheDocument();
		expect(screen.getByText("Active missions")).toBeInTheDocument();
	});

	it("lists recent admin actions", () => {
		mockUseDashboard.mockReturnValue({ data: summary, isLoading: false, isError: false });
		renderPage();
		expect(screen.getByText("Ban")).toBeInTheDocument();
		expect(screen.getByText("boss@x.com")).toBeInTheDocument();
	});

	it("shows an error state on failure", () => {
		mockUseDashboard.mockReturnValue({ data: undefined, isLoading: false, isError: true });
		renderPage();
		expect(screen.getByText("Couldn't load dashboard")).toBeInTheDocument();
	});
});
