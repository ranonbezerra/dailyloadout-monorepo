import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, type Mock, vi } from "vitest";
import type {
	AdminMissionDetail,
	AdminMissionList,
	AdminMissionSummary,
} from "../types/backoffice";
import { MissionsPage } from "./MissionsPage";

vi.mock("../hooks/useBackoffice", () => ({
	useMissions: vi.fn(),
	useMission: vi.fn(),
	useMissionActions: vi.fn(),
}));
vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

import { useMission, useMissionActions, useMissions } from "../hooks/useBackoffice";

const mockUseMissions = useMissions as Mock;
const mockUseMission = useMission as Mock;
const mockUseMissionActions = useMissionActions as Mock;

function mission(over: Partial<AdminMissionSummary> = {}): AdminMissionSummary {
	return {
		publicId: "m1",
		userEmail: "owner@example.com",
		gameTitle: "Hollow Knight",
		status: "active",
		missionType: "regular",
		endedVia: null,
		startedAt: new Date().toISOString(),
		endedAt: null,
		...over,
	};
}

function detail(over: Partial<AdminMissionDetail> = {}): AdminMissionDetail {
	return {
		...mission(),
		platformLabel: "PC",
		briefingText: "Beat the boss",
		debriefText: null,
		hasExtractedState: false,
		...over,
	};
}

function list(items: AdminMissionSummary[]): AdminMissionList {
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
			<MissionsPage />
		</MantineProvider>,
	);
}

describe("MissionsPage", () => {
	it("renders tallies and a mission row", () => {
		mockUseMissionActions.mockReturnValue(actions());
		mockUseMission.mockReturnValue({ data: undefined, isLoading: false });
		mockUseMissions.mockReturnValue({ data: list([mission()]), isLoading: false, isError: false });
		renderPage();
		expect(screen.getByText("owner@example.com")).toBeInTheDocument();
		expect(screen.getByText("Hollow Knight")).toBeInTheDocument();
		expect(screen.getAllByText("active").length).toBeGreaterThan(0);
	});

	it("shows an empty state", () => {
		mockUseMissionActions.mockReturnValue(actions());
		mockUseMission.mockReturnValue({ data: undefined, isLoading: false });
		mockUseMissions.mockReturnValue({ data: list([]), isLoading: false, isError: false });
		renderPage();
		expect(screen.getByText("No missions match.")).toBeInTheDocument();
	});

	it("loading and error states render", () => {
		mockUseMissionActions.mockReturnValue(actions());
		mockUseMission.mockReturnValue({ data: undefined, isLoading: false });
		mockUseMissions.mockReturnValue({ data: undefined, isLoading: true, isError: false });
		const { rerender } = renderPage();
		mockUseMissions.mockReturnValue({ data: undefined, isLoading: false, isError: true });
		rerender(
			<MantineProvider>
				<MissionsPage />
			</MantineProvider>,
		);
		expect(screen.getByText("Failed to load missions.")).toBeInTheDocument();
	});

	it("clamps an active mission via the confirm modal", async () => {
		const a = actions();
		a.clamp.mutate = vi.fn((_id, opts) => opts?.onSuccess?.());
		mockUseMissionActions.mockReturnValue(a);
		mockUseMission.mockReturnValue({ data: undefined, isLoading: false });
		mockUseMissions.mockReturnValue({ data: list([mission()]), isLoading: false, isError: false });
		renderPage();
		fireEvent.click(screen.getByLabelText("Clamp mission"));
		fireEvent.click(await screen.findByRole("button", { name: "Clamp" }));
		expect(a.clamp.mutate).toHaveBeenCalledWith("m1", expect.anything());
	});

	it("surfaces a clamp error", async () => {
		const a = actions();
		a.clamp.mutate = vi.fn((_id, opts) => opts?.onError?.(new Error("already ended")));
		mockUseMissionActions.mockReturnValue(a);
		mockUseMission.mockReturnValue({ data: undefined, isLoading: false });
		mockUseMissions.mockReturnValue({ data: list([mission()]), isLoading: false, isError: false });
		renderPage();
		fireEvent.click(screen.getByLabelText("Clamp mission"));
		fireEvent.click(await screen.findByRole("button", { name: "Clamp" }));
		expect(a.clamp.mutate).toHaveBeenCalled();
	});

	it("hides clamp for an ended mission and shows its detail", async () => {
		mockUseMissionActions.mockReturnValue(actions());
		mockUseMission.mockReturnValue({
			data: detail({
				status: "ended",
				endedVia: "debrief_completed",
				endedAt: new Date().toISOString(),
			}),
			isLoading: false,
		});
		mockUseMissions.mockReturnValue({
			data: list([mission({ status: "ended", endedVia: "debrief_completed" })]),
			isLoading: false,
			isError: false,
		});
		renderPage();
		expect(screen.queryByLabelText("Clamp mission")).not.toBeInTheDocument();
		fireEvent.click(screen.getByLabelText("View"));
		expect(await screen.findByText("Beat the boss")).toBeInTheDocument();
	});

	it("shows pagination summary when there are many missions", () => {
		mockUseMissionActions.mockReturnValue(actions());
		mockUseMission.mockReturnValue({ data: undefined, isLoading: false });
		mockUseMissions.mockReturnValue({
			data: { ...list([mission()]), total: 50 },
			isLoading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getByText("50 missions")).toBeInTheDocument();
	});
});
