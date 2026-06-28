import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QuickAddMenu } from "./QuickAddMenu";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeProps() {
	return {
		onManual: vi.fn(),
		onText: vi.fn(),
		onVoice: vi.fn(),
		onImage: vi.fn(),
	};
}

function renderMenu(props = makeProps()) {
	return {
		...render(
			<MantineProvider>
				<QuickAddMenu {...props} />
			</MantineProvider>,
		),
		props,
	};
}

/**
 * Opens the Mantine Menu dropdown by clicking the trigger button.
 *
 * Mantine renders the dropdown inside a portal with a CSS transition.
 * In jsdom the transition never fires so the dropdown stays `display: none`.
 * The DOM content IS present though, so text queries work after waiting.
 */
async function openMenu() {
	fireEvent.click(screen.getByRole("button", { name: /quick add/i }));
	// Wait until the dropdown text is in the DOM
	await waitFor(() => {
		expect(screen.getByText("Add manually")).toBeInTheDocument();
	});
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("QuickAddMenu", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('renders "Quick Add" button', () => {
		renderMenu();

		expect(screen.getByRole("button", { name: /quick add/i })).toBeInTheDocument();
	});

	it('clicking "Quick Add" opens the menu dropdown', async () => {
		renderMenu();

		// Menu items should not be visible initially
		expect(screen.queryByText("Add manually")).not.toBeInTheDocument();

		await openMenu();

		expect(screen.getByText("Add manually")).toBeInTheDocument();
		expect(screen.getByText("Describe in text")).toBeInTheDocument();
		expect(screen.getByText("Voice")).toBeInTheDocument();
		expect(screen.getByText("Photo or screenshot")).toBeInTheDocument();
	});

	it("shows the manual and AI-capture options when opened", async () => {
		renderMenu();
		await openMenu();

		for (const label of ["Add manually", "Describe in text", "Voice", "Photo or screenshot"]) {
			expect(screen.getByText(label)).toBeInTheDocument();
		}
	});

	it("clicking Add manually calls onManual", async () => {
		const { props } = renderMenu();
		await openMenu();

		fireEvent.click(screen.getByText("Add manually"));

		expect(props.onManual).toHaveBeenCalledOnce();
		expect(props.onText).not.toHaveBeenCalled();
	});

	it("clicking Describe in text calls onText", async () => {
		const { props } = renderMenu();
		await openMenu();

		fireEvent.click(screen.getByText("Describe in text"));

		expect(props.onText).toHaveBeenCalledOnce();
		expect(props.onManual).not.toHaveBeenCalled();
		expect(props.onVoice).not.toHaveBeenCalled();
		expect(props.onImage).not.toHaveBeenCalled();
	});

	it("clicking Voice calls onVoice", async () => {
		const { props } = renderMenu();
		await openMenu();

		fireEvent.click(screen.getByText("Voice"));

		expect(props.onVoice).toHaveBeenCalledOnce();
		expect(props.onText).not.toHaveBeenCalled();
		expect(props.onImage).not.toHaveBeenCalled();
	});

	it("clicking Photo or screenshot calls onImage", async () => {
		const { props } = renderMenu();
		await openMenu();

		fireEvent.click(screen.getByText("Photo or screenshot"));

		expect(props.onImage).toHaveBeenCalledOnce();
		expect(props.onText).not.toHaveBeenCalled();
		expect(props.onVoice).not.toHaveBeenCalled();
	});
});
