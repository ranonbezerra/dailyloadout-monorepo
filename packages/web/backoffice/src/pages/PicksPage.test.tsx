import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, type Mock, vi } from "vitest";
import type { AdminPickDetail, AdminPickList, AdminPickSummary } from "../types/backoffice";
import { PicksPage } from "./PicksPage";

vi.mock("../hooks/useBackoffice", () => ({
	usePicks: vi.fn(),
	usePick: vi.fn(),
}));

import { usePick, usePicks } from "../hooks/useBackoffice";

const mockUsePicks = usePicks as Mock;
const mockUsePick = usePick as Mock;

function pick(over: Partial<AdminPickSummary> = {}): AdminPickSummary {
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

function detail(over: Partial<AdminPickDetail> = {}): AdminPickDetail {
	return {
		...pick(),
		platformLabel: "PC",
		context: "after work",
		reasoning: "A calm metroidvania for a focused hour.",
		ledToPlaySession: false,
		...over,
	};
}

function list(items: AdminPickSummary[]): AdminPickList {
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
			<PicksPage />
		</MantineProvider>,
	);
}

describe("PicksPage", () => {
	it("renders tallies and a pick row", () => {
		mockUsePick.mockReturnValue({ data: undefined, isLoading: false });
		mockUsePicks.mockReturnValue({ data: list([pick()]), isLoading: false, isError: false });
		renderPage();
		expect(screen.getByText("owner@example.com")).toBeInTheDocument();
		expect(screen.getByText("Hollow Knight")).toBeInTheDocument();
		expect(screen.getAllByText("pending").length).toBeGreaterThan(0);
	});

	it("shows an empty state", () => {
		mockUsePick.mockReturnValue({ data: undefined, isLoading: false });
		mockUsePicks.mockReturnValue({ data: list([]), isLoading: false, isError: false });
		renderPage();
		expect(screen.getByText("No picks match.")).toBeInTheDocument();
	});

	it("loading and error states render", () => {
		mockUsePick.mockReturnValue({ data: undefined, isLoading: false });
		mockUsePicks.mockReturnValue({ data: undefined, isLoading: true, isError: false });
		const { rerender } = renderPage();
		mockUsePicks.mockReturnValue({ data: undefined, isLoading: false, isError: true });
		rerender(
			<MantineProvider>
				<PicksPage />
			</MantineProvider>,
		);
		expect(screen.getByText("Failed to load picks.")).toBeInTheDocument();
	});

	it("opens the detail drawer with reasoning and led-to-playSession", async () => {
		mockUsePick.mockReturnValue({
			data: detail({ ledToPlaySession: true }),
			isLoading: false,
		});
		mockUsePicks.mockReturnValue({ data: list([pick()]), isLoading: false, isError: false });
		renderPage();
		fireEvent.click(screen.getByLabelText("View"));
		expect(await screen.findByText("A calm metroidvania for a focused hour.")).toBeInTheDocument();
		expect(screen.getByText("led to session")).toBeInTheDocument();
	});

	it("updates the search box on input", () => {
		mockUsePick.mockReturnValue({ data: undefined, isLoading: false });
		mockUsePicks.mockReturnValue({ data: list([pick()]), isLoading: false, isError: false });
		renderPage();
		const box = screen.getByPlaceholderText("Search by owner email…");
		fireEvent.change(box, { target: { value: "alice" } });
		expect(box).toHaveValue("alice");
	});

	it("shows pagination summary when there are many picks", () => {
		mockUsePick.mockReturnValue({ data: undefined, isLoading: false });
		mockUsePicks.mockReturnValue({
			data: { ...list([pick()]), total: 50 },
			isLoading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getByText("50 picks")).toBeInTheDocument();
	});
});
