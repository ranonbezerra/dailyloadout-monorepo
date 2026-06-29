import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, type Mock, vi } from "vitest";
import type {
	AdminPlaySessionDetail,
	AdminPlaySessionList,
	AdminPlaySessionSummary,
} from "../types/backoffice";
import { PlaySessionsPage } from "./PlaySessionsPage";

vi.mock("../hooks/useBackoffice", () => ({
	usePlaySessions: vi.fn(),
	usePlaySession: vi.fn(),
	usePlaySessionActions: vi.fn(),
}));
vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

import { usePlaySession, usePlaySessionActions, usePlaySessions } from "../hooks/useBackoffice";

const mockUsePlaySessions = usePlaySessions as Mock;
const mockUsePlaySession = usePlaySession as Mock;
const mockUsePlaySessionActions = usePlaySessionActions as Mock;

function playSession(over: Partial<AdminPlaySessionSummary> = {}): AdminPlaySessionSummary {
	return {
		publicId: "m1",
		userEmail: "owner@example.com",
		gameTitle: "Hollow Knight",
		status: "active",
		playSessionType: "regular",
		endedVia: null,
		startedAt: new Date().toISOString(),
		endedAt: null,
		...over,
	};
}

function detail(over: Partial<AdminPlaySessionDetail> = {}): AdminPlaySessionDetail {
	return {
		...playSession(),
		platformLabel: "PC",
		recapText: "Beat the boss",
		wrapUpText: null,
		hasExtractedState: false,
		...over,
	};
}

function list(items: AdminPlaySessionSummary[]): AdminPlaySessionList {
	return {
		items,
		total: items.length,
		limit: 20,
		offset: 0,
		statusCounts: [
			{ status: "active", count: items.filter((m) => m.status === "active").length },
			{ status: "ended", count: items.filter((m) => m.status === "ended").length },
		],
	};
}

function actions() {
	return { clamp: { mutate: vi.fn(), isPending: false } };
}

function renderPage() {
	return render(
		<MantineProvider>
			<PlaySessionsPage />
		</MantineProvider>,
	);
}

describe("PlaySessionsPage", () => {
	it("renders tallies and a playSession row", () => {
		mockUsePlaySessionActions.mockReturnValue(actions());
		mockUsePlaySession.mockReturnValue({ data: undefined, isLoading: false });
		mockUsePlaySessions.mockReturnValue({
			data: list([playSession()]),
			isLoading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getByText("owner@example.com")).toBeInTheDocument();
		expect(screen.getByText("Hollow Knight")).toBeInTheDocument();
		expect(screen.getAllByText("active").length).toBeGreaterThan(0);
	});

	it("shows an empty state", () => {
		mockUsePlaySessionActions.mockReturnValue(actions());
		mockUsePlaySession.mockReturnValue({ data: undefined, isLoading: false });
		mockUsePlaySessions.mockReturnValue({ data: list([]), isLoading: false, isError: false });
		renderPage();
		expect(screen.getByText("No sessions match.")).toBeInTheDocument();
	});

	it("loading and error states render", () => {
		mockUsePlaySessionActions.mockReturnValue(actions());
		mockUsePlaySession.mockReturnValue({ data: undefined, isLoading: false });
		mockUsePlaySessions.mockReturnValue({ data: undefined, isLoading: true, isError: false });
		const { rerender } = renderPage();
		mockUsePlaySessions.mockReturnValue({ data: undefined, isLoading: false, isError: true });
		rerender(
			<MantineProvider>
				<PlaySessionsPage />
			</MantineProvider>,
		);
		expect(screen.getByText("Failed to load sessions.")).toBeInTheDocument();
	});

	it("clamps an active playSession via the confirm modal", async () => {
		const a = actions();
		a.clamp.mutate = vi.fn((_id, opts) => opts?.onSuccess?.());
		mockUsePlaySessionActions.mockReturnValue(a);
		mockUsePlaySession.mockReturnValue({ data: undefined, isLoading: false });
		mockUsePlaySessions.mockReturnValue({
			data: list([playSession()]),
			isLoading: false,
			isError: false,
		});
		renderPage();
		fireEvent.click(screen.getByLabelText("Clamp playSession"));
		fireEvent.click(await screen.findByRole("button", { name: "Clamp" }));
		expect(a.clamp.mutate).toHaveBeenCalledWith("m1", expect.anything());
	});

	it("surfaces a clamp error", async () => {
		const a = actions();
		a.clamp.mutate = vi.fn((_id, opts) => opts?.onError?.(new Error("already ended")));
		mockUsePlaySessionActions.mockReturnValue(a);
		mockUsePlaySession.mockReturnValue({ data: undefined, isLoading: false });
		mockUsePlaySessions.mockReturnValue({
			data: list([playSession()]),
			isLoading: false,
			isError: false,
		});
		renderPage();
		fireEvent.click(screen.getByLabelText("Clamp playSession"));
		fireEvent.click(await screen.findByRole("button", { name: "Clamp" }));
		expect(a.clamp.mutate).toHaveBeenCalled();
	});

	it("hides clamp for an ended playSession and shows its detail", async () => {
		mockUsePlaySessionActions.mockReturnValue(actions());
		mockUsePlaySession.mockReturnValue({
			data: detail({
				status: "ended",
				endedVia: "wrap_up_completed",
				endedAt: new Date().toISOString(),
			}),
			isLoading: false,
		});
		mockUsePlaySessions.mockReturnValue({
			data: list([playSession({ status: "ended", endedVia: "wrap_up_completed" })]),
			isLoading: false,
			isError: false,
		});
		renderPage();
		expect(screen.queryByLabelText("Clamp playSession")).not.toBeInTheDocument();
		fireEvent.click(screen.getByLabelText("View"));
		expect(await screen.findByText("Beat the boss")).toBeInTheDocument();
	});

	it("shows pagination summary when there are many playSessions", () => {
		mockUsePlaySessionActions.mockReturnValue(actions());
		mockUsePlaySession.mockReturnValue({ data: undefined, isLoading: false });
		mockUsePlaySessions.mockReturnValue({
			data: { ...list([playSession()]), total: 50 },
			isLoading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getByText("50 playSessions")).toBeInTheDocument();
	});
});
