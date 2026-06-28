import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, type Mock, vi } from "vitest";
import type {
	AdminLoadoutDetail,
	AdminLoadoutList,
	AdminLoadoutSummary,
} from "../types/backoffice";
import { LoadoutsPage } from "./LoadoutsPage";

vi.mock("../hooks/useBackoffice", () => ({
	useLoadouts: vi.fn(),
	useLoadout: vi.fn(),
}));

import { useLoadout, useLoadouts } from "../hooks/useBackoffice";

const mockUseLoadouts = useLoadouts as Mock;
const mockUseLoadout = useLoadout as Mock;

function loadout(over: Partial<AdminLoadoutSummary> = {}): AdminLoadoutSummary {
	return {
		publicId: "l1",
		userEmail: "owner@example.com",
		gameTitle: "Hollow Knight",
		action: "pending",
		mood: "chill",
		availableMinutes: 60,
		mentalEnergy: "medium",
		createdAt: new Date().toISOString(),
		...over,
	};
}

function detail(over: Partial<AdminLoadoutDetail> = {}): AdminLoadoutDetail {
	return {
		...loadout(),
		platformLabel: "PC",
		context: "after work",
		reasoning: "A calm metroidvania for a focused hour.",
		ledToMission: false,
		...over,
	};
}

function list(items: AdminLoadoutSummary[]): AdminLoadoutList {
	return {
		items,
		total: items.length,
		limit: 20,
		offset: 0,
		actionCounts: [{ action: "pending", count: items.length }],
	};
}

function renderPage() {
	return render(
		<MantineProvider>
			<LoadoutsPage />
		</MantineProvider>,
	);
}

describe("LoadoutsPage", () => {
	it("renders tallies and a loadout row", () => {
		mockUseLoadout.mockReturnValue({ data: undefined, isLoading: false });
		mockUseLoadouts.mockReturnValue({ data: list([loadout()]), isLoading: false, isError: false });
		renderPage();
		expect(screen.getByText("owner@example.com")).toBeInTheDocument();
		expect(screen.getByText("Hollow Knight")).toBeInTheDocument();
		expect(screen.getAllByText("pending").length).toBeGreaterThan(0);
	});

	it("shows an empty state", () => {
		mockUseLoadout.mockReturnValue({ data: undefined, isLoading: false });
		mockUseLoadouts.mockReturnValue({ data: list([]), isLoading: false, isError: false });
		renderPage();
		expect(screen.getByText("No loadouts match.")).toBeInTheDocument();
	});

	it("loading and error states render", () => {
		mockUseLoadout.mockReturnValue({ data: undefined, isLoading: false });
		mockUseLoadouts.mockReturnValue({ data: undefined, isLoading: true, isError: false });
		const { rerender } = renderPage();
		mockUseLoadouts.mockReturnValue({ data: undefined, isLoading: false, isError: true });
		rerender(
			<MantineProvider>
				<LoadoutsPage />
			</MantineProvider>,
		);
		expect(screen.getByText("Failed to load loadouts.")).toBeInTheDocument();
	});

	it("opens the detail drawer with reasoning and led-to-mission", async () => {
		mockUseLoadout.mockReturnValue({
			data: detail({ ledToMission: true }),
			isLoading: false,
		});
		mockUseLoadouts.mockReturnValue({ data: list([loadout()]), isLoading: false, isError: false });
		renderPage();
		fireEvent.click(screen.getByLabelText("View"));
		expect(await screen.findByText("A calm metroidvania for a focused hour.")).toBeInTheDocument();
		expect(screen.getByText("led to mission")).toBeInTheDocument();
	});

	it("updates the search box on input", () => {
		mockUseLoadout.mockReturnValue({ data: undefined, isLoading: false });
		mockUseLoadouts.mockReturnValue({ data: list([loadout()]), isLoading: false, isError: false });
		renderPage();
		const box = screen.getByPlaceholderText("Search by owner email…");
		fireEvent.change(box, { target: { value: "alice" } });
		expect(box).toHaveValue("alice");
	});

	it("shows pagination summary when there are many loadouts", () => {
		mockUseLoadout.mockReturnValue({ data: undefined, isLoading: false });
		mockUseLoadouts.mockReturnValue({
			data: { ...list([loadout()]), total: 50 },
			isLoading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getByText("50 loadouts")).toBeInTheDocument();
	});
});
