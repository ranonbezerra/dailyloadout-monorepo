import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, type Mock, vi } from "vitest";
import type { AdminGameList, AdminGameSummary } from "../../types/backoffice";
import { GamesPage } from "./GamesPage";

vi.mock("../../hooks/useBackoffice", () => ({
	useGames: vi.fn(),
	useGameActions: vi.fn(),
}));
vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

import { useGameActions, useGames } from "../../hooks/useBackoffice";

const mockUseGames = useGames as Mock;
const mockUseGameActions = useGameActions as Mock;

function game(over: Partial<AdminGameSummary> = {}): AdminGameSummary {
	return {
		publicId: "g1",
		slug: "halo",
		title: "Halo",
		igdbId: 111,
		source: "igdb",
		isShared: true,
		coverUrl: null,
		ownerCount: 4,
		createdAt: new Date().toISOString(),
		...over,
	};
}

function list(items: AdminGameSummary[]): AdminGameList {
	return {
		items,
		total: items.length,
		limit: 20,
		offset: 0,
		catalogueTotal: items.length,
		catalogueIgdb: items.filter((g) => g.source === "igdb").length,
		catalogueManual: items.filter((g) => g.source === "manual").length,
	};
}

function actions() {
	return {
		demote: { mutate: vi.fn(), isPending: false },
		promote: { mutate: vi.fn(), isPending: false },
		edit: { mutate: vi.fn(), isPending: false },
	};
}

function renderPage() {
	return render(
		<MantineProvider>
			<GamesPage />
		</MantineProvider>,
	);
}

describe("GamesPage", () => {
	it("renders catalogue tallies and a game row", () => {
		mockUseGameActions.mockReturnValue(actions());
		mockUseGames.mockReturnValue({ data: list([game()]), isLoading: false, isError: false });
		renderPage();
		expect(screen.getByText("Halo")).toBeInTheDocument();
		expect(screen.getByText("shared")).toBeInTheDocument();
		expect(screen.getByText("Total games")).toBeInTheDocument();
	});

	it("demotes a shared game", () => {
		const a = actions();
		mockUseGameActions.mockReturnValue(a);
		mockUseGames.mockReturnValue({ data: list([game()]), isLoading: false, isError: false });
		renderPage();
		fireEvent.click(screen.getByLabelText("Demote"));
		expect(a.demote.mutate).toHaveBeenCalledWith("g1", expect.anything());
	});

	it("promotes a private game", () => {
		const a = actions();
		mockUseGameActions.mockReturnValue(a);
		mockUseGames.mockReturnValue({
			data: list([game({ isShared: false, source: "manual", igdbId: null })]),
			isLoading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getByText("private")).toBeInTheDocument();
		fireEvent.click(screen.getByLabelText("Promote"));
		expect(a.promote.mutate).toHaveBeenCalledWith("g1", expect.anything());
	});

	it("shows an empty state", () => {
		mockUseGameActions.mockReturnValue(actions());
		mockUseGames.mockReturnValue({ data: list([]), isLoading: false, isError: false });
		renderPage();
		expect(screen.getByText("No games match.")).toBeInTheDocument();
	});
});
