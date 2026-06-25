import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QuickAddMenu } from "./QuickAddMenu";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeProps() {
	return {
		onText: vi.fn(),
		onVoice: vi.fn(),
		onPhoto: vi.fn(),
		onImport: vi.fn(),
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
		expect(screen.getByText("Text")).toBeInTheDocument();
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
		expect(screen.queryByText("Text")).not.toBeInTheDocument();

		await openMenu();

		expect(screen.getByText("Text")).toBeInTheDocument();
		expect(screen.getByText("Voice")).toBeInTheDocument();
		expect(screen.getByText("Photo")).toBeInTheDocument();
	});

	it("menu shows Text, Voice, and Photo items when opened", async () => {
		renderMenu();
		await openMenu();

		// Verify all three menu item labels are in the DOM
		for (const label of ["Text", "Voice", "Photo"]) {
			expect(screen.getByText(label)).toBeInTheDocument();
		}
	});

	it("clicking Text calls onText", async () => {
		const { props } = renderMenu();
		await openMenu();

		fireEvent.click(screen.getByText("Text"));

		expect(props.onText).toHaveBeenCalledOnce();
		expect(props.onVoice).not.toHaveBeenCalled();
		expect(props.onPhoto).not.toHaveBeenCalled();
	});

	it("clicking Voice calls onVoice", async () => {
		const { props } = renderMenu();
		await openMenu();

		fireEvent.click(screen.getByText("Voice"));

		expect(props.onVoice).toHaveBeenCalledOnce();
		expect(props.onText).not.toHaveBeenCalled();
		expect(props.onPhoto).not.toHaveBeenCalled();
	});

	it("clicking Photo calls onPhoto", async () => {
		const { props } = renderMenu();
		await openMenu();

		fireEvent.click(screen.getByText("Photo"));

		expect(props.onPhoto).toHaveBeenCalledOnce();
		expect(props.onText).not.toHaveBeenCalled();
		expect(props.onVoice).not.toHaveBeenCalled();
	});

	it("clicking Import from screenshots calls onImport", async () => {
		const { props } = renderMenu();
		await openMenu();

		fireEvent.click(screen.getByText("Import from screenshots"));

		expect(props.onImport).toHaveBeenCalledOnce();
		expect(props.onText).not.toHaveBeenCalled();
	});
});
