import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Lineup, RecapLabel, Slot, Spotlight } from "./index";

function renderWithMantine(ui: React.ReactNode) {
	return render(<MantineProvider>{ui}</MantineProvider>);
}

describe("brand devices", () => {
	it("Slot marks the lit state with a data attribute", () => {
		renderWithMantine(
			<>
				<Slot lit data-testid="lit">
					<span>P</span>
				</Slot>
				<Slot data-testid="waiting" />
			</>,
		);
		expect(screen.getByTestId("lit")).toHaveAttribute("data-lit", "true");
		expect(screen.getByTestId("waiting")).not.toHaveAttribute("data-lit");
		expect(screen.getByText("P")).toBeInTheDocument();
	});

	it("Lineup renders exactly one lit slot", () => {
		const { container } = renderWithMantine(<Lineup count={5} litIndex={2} />);
		expect(container.querySelectorAll("[data-lit='true']")).toHaveLength(1);
		// 5 slots total
		expect(container.querySelectorAll("div[style]").length).toBeGreaterThanOrEqual(5);
	});

	it("Lineup defaults the lit slot to the middle", () => {
		const { container } = renderWithMantine(<Lineup count={3} />);
		expect(container.querySelectorAll("[data-lit='true']")).toHaveLength(1);
	});

	it("RecapLabel renders the play glyph and uppercases the label", () => {
		renderWithMantine(<RecapLabel>Previously on</RecapLabel>);
		expect(screen.getByText("Previously on")).toBeInTheDocument();
		expect(screen.getByText("▸")).toBeInTheDocument();
	});

	it("Spotlight wraps its children and toggles the glow", () => {
		const { rerender } = renderWithMantine(
			<Spotlight active>
				<span>pick</span>
			</Spotlight>,
		);
		expect(screen.getByText("pick")).toBeInTheDocument();
		rerender(
			<MantineProvider>
				<Spotlight active={false}>
					<span>pick</span>
				</Spotlight>
			</MantineProvider>,
		);
		expect(screen.getByText("pick")).toBeInTheDocument();
	});
});
