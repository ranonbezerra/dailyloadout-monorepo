import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

// ---------------------------------------------------------------------------
// A child component that throws on demand
// ---------------------------------------------------------------------------

function ThrowingChild({ shouldThrow }: { shouldThrow: boolean }) {
	if (shouldThrow) {
		throw new Error("Test explosion");
	}
	return <div data-testid="happy-child">All good</div>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderWithBoundary(shouldThrow = false) {
	return render(
		<MantineProvider>
			<ErrorBoundary>
				<ThrowingChild shouldThrow={shouldThrow} />
			</ErrorBoundary>
		</MantineProvider>,
	);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ErrorBoundary", () => {
	beforeEach(() => {
		// Suppress React's noisy error boundary logging during tests
		vi.spyOn(console, "error").mockImplementation(() => {});
	});

	it("renders children when no error occurs", () => {
		renderWithBoundary(false);

		expect(screen.getByTestId("happy-child")).toBeInTheDocument();
		expect(screen.getByText("All good")).toBeInTheDocument();
		expect(screen.queryByText("Something went wrong")).not.toBeInTheDocument();
	});

	it('shows "Something went wrong" when a child throws', () => {
		renderWithBoundary(true);

		expect(screen.getByText("Something went wrong")).toBeInTheDocument();
		expect(screen.queryByTestId("happy-child")).not.toBeInTheDocument();
	});

	it("displays the error message from the thrown error", () => {
		renderWithBoundary(true);

		expect(screen.getByText("Test explosion")).toBeInTheDocument();
	});

	it('"Try again" button resets the error and re-renders children', () => {
		// We need a stateful wrapper so ThrowingChild can stop throwing after reset
		let shouldThrow = true;

		function ToggleChild() {
			if (shouldThrow) {
				throw new Error("Kaboom");
			}
			return <div data-testid="recovered-child">Recovered</div>;
		}

		render(
			<MantineProvider>
				<ErrorBoundary>
					<ToggleChild />
				</ErrorBoundary>
			</MantineProvider>,
		);

		// Error state is shown
		expect(screen.getByText("Something went wrong")).toBeInTheDocument();

		// Now stop throwing before pressing "Try again"
		shouldThrow = false;

		fireEvent.click(screen.getByRole("button", { name: /try again/i }));

		// After reset, children should render successfully
		expect(screen.getByTestId("recovered-child")).toBeInTheDocument();
		expect(screen.queryByText("Something went wrong")).not.toBeInTheDocument();
	});

	it("componentDidCatch logs to console.error", () => {
		const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

		renderWithBoundary(true);

		// React calls console.error internally AND our componentDidCatch calls it
		// Find our specific call
		const ourCall = consoleSpy.mock.calls.find((args) => args[0] === "ErrorBoundary caught:");
		expect(ourCall).toBeDefined();
		expect(ourCall?.[1]).toBeInstanceOf(Error);
		expect(ourCall?.[1].message).toBe("Test explosion");
	});
});
