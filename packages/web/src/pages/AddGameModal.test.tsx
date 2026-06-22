import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AddGameModal } from "./AddGameModal";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

vi.mock("@mantine/hooks", () => ({
	useDebouncedValue: vi.fn((value: string) => [value]),
}));

vi.mock("../hooks/useLibrary", () => ({
	useAddToLibrary: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
	useCreateGame: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
	useGameGenres: vi.fn(() => ({
		data: ["RPG", "Action", "Adventure"],
	})),
	usePlatforms: vi.fn(() => ({
		data: [
			{ id: 1, slug: "pc", label: "PC", family: "desktop" },
			{ id: 2, slug: "ps5", label: "PlayStation 5", family: "console" },
		],
	})),
	useSearchGames: vi.fn(() => ({
		data: [],
		isFetching: false,
	})),
}));

// ---------------------------------------------------------------------------
// Polyfills for Mantine Textarea autosize in jsdom
// ---------------------------------------------------------------------------

if (typeof globalThis.ResizeObserver === "undefined") {
	globalThis.ResizeObserver = class ResizeObserver {
		observe() {}
		unobserve() {}
		disconnect() {}
	} as unknown as typeof ResizeObserver;
}

// Mantine Autosize accesses document.fonts.addEventListener which is
// undefined in jsdom.
if (!document.fonts) {
	Object.defineProperty(document, "fonts", {
		value: {
			addEventListener: () => {},
			removeEventListener: () => {},
		},
	});
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const defaultProps = {
	opened: true,
	onClose: vi.fn(),
};

function renderModal(props = defaultProps) {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<AddGameModal {...props} />
			</MemoryRouter>
		</MantineProvider>,
	);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AddGameModal", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("does not render modal content when opened is false", () => {
		renderModal({ opened: false, onClose: vi.fn() });

		expect(screen.queryByText("Add Game to Library")).not.toBeInTheDocument();
	});

	it('shows "Add Game to Library" title when opened', () => {
		renderModal();

		expect(screen.getByText("Add Game to Library")).toBeInTheDocument();
	});

	it("shows search input in search mode (default)", () => {
		renderModal();

		expect(screen.getByPlaceholderText("Type at least 2 characters...")).toBeInTheDocument();
	});

	it('shows "Create manually" switch', () => {
		renderModal();

		expect(screen.getByText("Create manually")).toBeInTheDocument();
	});

	it("shows Title and Slug inputs in manual mode", () => {
		renderModal();

		// Toggle to manual mode -- Mantine Switch renders as role="switch"
		const toggle = screen.getByRole("switch", { name: /create manually/i });
		fireEvent.click(toggle);

		expect(screen.getByPlaceholderText("Game title")).toBeInTheDocument();
		expect(screen.getByPlaceholderText("game-slug")).toBeInTheDocument();
	});

	it("shows platform select, status select, and notes textarea", () => {
		renderModal();

		expect(screen.getByText("Platform")).toBeInTheDocument();
		expect(screen.getByText("Status")).toBeInTheDocument();
		expect(screen.getByText("Notes")).toBeInTheDocument();
		expect(screen.getByPlaceholderText("Optional notes...")).toBeInTheDocument();
	});

	it('shows "Add to Library" button', () => {
		renderModal();

		expect(screen.getByRole("button", { name: /add to library/i })).toBeInTheDocument();
	});
});
