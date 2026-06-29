import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AiRecapOverlay } from "./AiRecapOverlay";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderOverlay(props: { opened: boolean; gameTitle?: string }) {
	return render(
		<MantineProvider>
			<AiRecapOverlay {...props} />
		</MantineProvider>,
	);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AiRecapOverlay", () => {
	it("does not show modal content when opened is false", () => {
		renderOverlay({ opened: false });

		expect(screen.queryByText("Preparing your recap")).not.toBeInTheDocument();
	});

	it('shows "Preparing your recap" when opened is true', () => {
		renderOverlay({ opened: true });

		expect(screen.getByText("Preparing your recap")).toBeInTheDocument();
	});

	it("shows game-specific message when gameTitle is provided", () => {
		renderOverlay({ opened: true, gameTitle: "Elden Ring" });

		expect(
			screen.getByText(
				"Analyzing your previous sessions in Elden Ring to craft a personalized recap.",
			),
		).toBeInTheDocument();
	});

	it("shows generic message when no gameTitle is provided", () => {
		renderOverlay({ opened: true });

		expect(
			screen.getByText("Analyzing your previous sessions to craft a personalized recap."),
		).toBeInTheDocument();

		expect(screen.queryByText(/Analyzing your previous sessions in/)).not.toBeInTheDocument();
	});
});
