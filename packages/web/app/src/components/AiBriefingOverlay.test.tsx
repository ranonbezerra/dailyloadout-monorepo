import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AiBriefingOverlay } from "./AiBriefingOverlay";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderOverlay(props: { opened: boolean; gameTitle?: string }) {
	return render(
		<MantineProvider>
			<AiBriefingOverlay {...props} />
		</MantineProvider>,
	);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AiBriefingOverlay", () => {
	it("does not show modal content when opened is false", () => {
		renderOverlay({ opened: false });

		expect(screen.queryByText("AI is preparing your briefing")).not.toBeInTheDocument();
	});

	it('shows "AI is preparing your briefing" when opened is true', () => {
		renderOverlay({ opened: true });

		expect(screen.getByText("AI is preparing your briefing")).toBeInTheDocument();
	});

	it("shows game-specific message when gameTitle is provided", () => {
		renderOverlay({ opened: true, gameTitle: "Elden Ring" });

		expect(
			screen.getByText(
				"Analyzing your previous sessions in Elden Ring to craft a personalized briefing.",
			),
		).toBeInTheDocument();
	});

	it("shows generic message when no gameTitle is provided", () => {
		renderOverlay({ opened: true });

		expect(
			screen.getByText("Analyzing your previous sessions to craft a personalized briefing."),
		).toBeInTheDocument();

		expect(screen.queryByText(/Analyzing your previous sessions in/)).not.toBeInTheDocument();
	});
});
