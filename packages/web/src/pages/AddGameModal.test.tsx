import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type React from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	useAddToLibrary,
	useCreateGame,
	useGameGenres,
	usePlatforms,
	useSearchGames,
} from "../hooks/useLibrary";
import type { Game } from "../types/library";
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

// Replace Mantine's combobox-driven Select / autosize Textarea / TagsInput with
// plain inputs so they can be driven deterministically with fireEvent in jsdom.
vi.mock("@mantine/core", async () => {
	const actual = await vi.importActual<typeof import("@mantine/core")>("@mantine/core");
	return {
		...actual,
		Select: ({
			label,
			placeholder,
			value,
			onChange,
			data,
		}: {
			label?: string;
			placeholder?: string;
			value?: string | null;
			onChange?: (value: string | null) => void;
			data?: { value: string; label: string }[];
		}) => (
			<select
				aria-label={label}
				data-placeholder={placeholder}
				value={value ?? ""}
				onChange={(e) => onChange?.(e.currentTarget.value || null)}
			>
				<option value="">{placeholder ?? "—"}</option>
				{(data ?? []).map((opt) => (
					<option key={opt.value} value={opt.value}>
						{opt.label}
					</option>
				))}
			</select>
		),
		// Render MultiSelect as a native multi-select so tests can drive it.
		MultiSelect: ({
			label,
			placeholder,
			value,
			onChange,
			data,
		}: {
			label?: string;
			placeholder?: string;
			value?: string[];
			onChange?: (value: string[]) => void;
			data?: { value: string; label: string }[];
		}) => (
			<select
				multiple
				aria-label={label}
				data-placeholder={placeholder}
				value={value ?? []}
				onChange={(e) => onChange?.(Array.from(e.currentTarget.selectedOptions, (o) => o.value))}
			>
				{(data ?? []).map((opt) => (
					<option key={opt.value} value={opt.value}>
						{opt.label}
					</option>
				))}
			</select>
		),
		Textarea: ({
			label,
			placeholder,
			value,
			onChange,
		}: {
			label?: string;
			placeholder?: string;
			value?: string;
			onChange?: React.ChangeEventHandler<HTMLTextAreaElement>;
		}) => (
			<textarea aria-label={label} placeholder={placeholder} value={value} onChange={onChange} />
		),
		TagsInput: ({
			label,
			placeholder,
			value,
		}: {
			label?: string;
			placeholder?: string;
			value?: string[];
		}) => (
			<input
				aria-label={label}
				placeholder={placeholder}
				value={value?.join(",") ?? ""}
				readOnly
			/>
		),
	};
});

vi.mock("../hooks/useLibrary", () => ({
	useAddToLibrary: vi.fn(),
	useCreateGame: vi.fn(),
	useGameGenres: vi.fn(),
	usePlatforms: vi.fn(),
	useSearchGames: vi.fn(),
}));

const mockAddToLibrary = vi.mocked(useAddToLibrary);
const mockCreateGame = vi.mocked(useCreateGame);
const mockGameGenres = vi.mocked(useGameGenres);
const mockPlatforms = vi.mocked(usePlatforms);
const mockSearchGames = vi.mocked(useSearchGames);
const mockNotify = vi.mocked(notifications.show);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const SAMPLE_GAME: Game = {
	publicId: "game-1",
	slug: "hades",
	title: "Hades",
	summary: "Roguelike from Supergiant",
	metadataSource: "igdb",
	createdAt: "2024-01-01T00:00:00Z",
};

const PLATFORMS = [
	{ id: 1, slug: "pc", label: "PC", family: "desktop" },
	{ id: 2, slug: "ps5", label: "PlayStation 5", family: "console" },
];

let addMutateAsync: ReturnType<typeof vi.fn>;
let createMutateAsync: ReturnType<typeof vi.fn>;

interface SetupOpts {
	searchResults?: Game[];
	isSearching?: boolean;
	isAddPending?: boolean;
	isCreatePending?: boolean;
}

function setupHooks(opts: SetupOpts = {}) {
	addMutateAsync = vi.fn().mockResolvedValue({ publicId: "entry-1" });
	createMutateAsync = vi.fn().mockResolvedValue({ publicId: "created-game-1" });

	mockAddToLibrary.mockReturnValue({
		mutateAsync: addMutateAsync,
		isPending: opts.isAddPending ?? false,
	} as unknown as ReturnType<typeof useAddToLibrary>);
	mockCreateGame.mockReturnValue({
		mutateAsync: createMutateAsync,
		isPending: opts.isCreatePending ?? false,
	} as unknown as ReturnType<typeof useCreateGame>);
	mockGameGenres.mockReturnValue({
		data: ["RPG", "Action", "Adventure"],
	} as unknown as ReturnType<typeof useGameGenres>);
	mockPlatforms.mockReturnValue({
		data: PLATFORMS,
	} as unknown as ReturnType<typeof usePlatforms>);
	mockSearchGames.mockReturnValue({
		data: opts.searchResults ?? [],
		isFetching: opts.isSearching ?? false,
	} as unknown as ReturnType<typeof useSearchGames>);
}

function renderModal(props: { opened?: boolean; onClose?: () => void } = {}) {
	const onClose = props.onClose ?? vi.fn();
	const result = render(
		<MantineProvider>
			<MemoryRouter>
				<AddGameModal opened={props.opened ?? true} onClose={onClose} />
			</MemoryRouter>
		</MantineProvider>,
	);
	return { ...result, onClose };
}

function selectPlatforms(...labels: string[]) {
	const select = screen.getByRole("listbox", { name: "Platforms" }) as HTMLSelectElement;
	const wantedIds = labels.map((l) => String(PLATFORMS.find((p) => p.label === l)?.id));
	for (const option of Array.from(select.options)) {
		option.selected = wantedIds.includes(option.value);
	}
	fireEvent.change(select);
}

beforeEach(() => {
	vi.clearAllMocks();
	setupHooks();
});

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

describe("AddGameModal rendering", () => {
	it("does not render modal content when opened is false", () => {
		renderModal({ opened: false });
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

	it("shows the multi-platform select, status select, and notes textarea", () => {
		renderModal();
		expect(screen.getByRole("listbox", { name: "Platforms" })).toBeInTheDocument();
		expect(screen.getByRole("combobox", { name: "Status" })).toBeInTheDocument();
		expect(screen.getByPlaceholderText("Optional notes...")).toBeInTheDocument();
	});

	it("still renders the search field while results are fetching", () => {
		setupHooks({ isSearching: true });
		renderModal();
		expect(screen.getByPlaceholderText("Type at least 2 characters...")).toBeInTheDocument();
	});
});

// ---------------------------------------------------------------------------
// Search / typeahead
// ---------------------------------------------------------------------------

describe("AddGameModal search", () => {
	it("renders search results and selects one as a badge", () => {
		setupHooks({ searchResults: [SAMPLE_GAME] });
		renderModal();

		fireEvent.change(screen.getByPlaceholderText("Type at least 2 characters..."), {
			target: { value: "had" },
		});

		expect(screen.getByText("Roguelike from Supergiant")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Hades"));

		// Selected game becomes a badge with a clear "x" button.
		expect(screen.getByText("x")).toBeInTheDocument();
	});

	it("clears the selected game when the badge clear button is clicked", () => {
		setupHooks({ searchResults: [SAMPLE_GAME] });
		renderModal();

		fireEvent.click(screen.getByText("Hades"));
		expect(screen.getByText("x")).toBeInTheDocument();

		fireEvent.click(screen.getByText("x"));
		expect(screen.queryByText("x")).not.toBeInTheDocument();
	});
});

// ---------------------------------------------------------------------------
// Manual mode
// ---------------------------------------------------------------------------

describe("AddGameModal manual mode", () => {
	it("shows Title and Slug inputs in manual mode", () => {
		renderModal();
		fireEvent.click(screen.getByRole("switch", { name: /create manually/i }));
		expect(screen.getByPlaceholderText("Game title")).toBeInTheDocument();
		expect(screen.getByPlaceholderText("game-slug")).toBeInTheDocument();
	});
});

// ---------------------------------------------------------------------------
// Submit — search mode
// ---------------------------------------------------------------------------

describe("AddGameModal submit (search mode)", () => {
	it("warns when no platform is selected", () => {
		renderModal();

		fireEvent.click(screen.getByRole("button", { name: /add to library/i }));

		expect(mockNotify).toHaveBeenCalledWith(
			expect.objectContaining({ title: "Missing platform", color: "red" }),
		);
		expect(addMutateAsync).not.toHaveBeenCalled();
	});

	it("warns when a platform is set but no game is selected", () => {
		renderModal();

		selectPlatforms("PC");
		fireEvent.click(screen.getByRole("button", { name: /add to library/i }));

		expect(mockNotify).toHaveBeenCalledWith(
			expect.objectContaining({ title: "No game selected", color: "red" }),
		);
		expect(addMutateAsync).not.toHaveBeenCalled();
	});

	it("adds the selected game and closes on success", async () => {
		setupHooks({ searchResults: [SAMPLE_GAME] });
		const { onClose } = renderModal();

		fireEvent.click(screen.getByText("Hades"));
		selectPlatforms("PC");
		fireEvent.change(screen.getByPlaceholderText("Optional notes..."), {
			target: { value: "first run" },
		});

		fireEvent.click(screen.getByRole("button", { name: /add to library/i }));

		await waitFor(() => {
			expect(addMutateAsync).toHaveBeenCalledWith({
				gamePublicId: "game-1",
				platformIds: [1],
				status: "backlog",
				notes: "first run",
			});
		});
		expect(mockNotify).toHaveBeenCalledWith(
			expect.objectContaining({ title: "Added to library", color: "green" }),
		);
		expect(onClose).toHaveBeenCalled();
	});

	it("adds the selected game on multiple platforms at once", async () => {
		setupHooks({ searchResults: [SAMPLE_GAME] });
		renderModal();

		fireEvent.click(screen.getByText("Hades"));
		selectPlatforms("PC", "PlayStation 5");

		fireEvent.click(screen.getByRole("button", { name: /add to library/i }));

		await waitFor(() => {
			expect(addMutateAsync).toHaveBeenCalledWith({
				gamePublicId: "game-1",
				platformIds: [1, 2],
				status: "backlog",
				notes: undefined,
			});
		});
	});

	it("shows an error notification when the mutation rejects", async () => {
		setupHooks({ searchResults: [SAMPLE_GAME] });
		addMutateAsync.mockRejectedValueOnce(new Error("boom"));
		renderModal();

		fireEvent.click(screen.getByText("Hades"));
		selectPlatforms("PC");
		fireEvent.click(screen.getByRole("button", { name: /add to library/i }));

		await waitFor(() => {
			expect(mockNotify).toHaveBeenCalledWith(
				expect.objectContaining({ title: "Failed to add game", message: "boom", color: "red" }),
			);
		});
	});
});

// ---------------------------------------------------------------------------
// Submit — manual mode
// ---------------------------------------------------------------------------

describe("AddGameModal submit (manual mode)", () => {
	it("warns when manual title/slug are empty", () => {
		renderModal();

		fireEvent.click(screen.getByRole("switch", { name: /create manually/i }));
		selectPlatforms("PC");
		fireEvent.click(screen.getByRole("button", { name: /add to library/i }));

		expect(mockNotify).toHaveBeenCalledWith(
			expect.objectContaining({ title: "Missing fields", color: "red" }),
		);
		expect(createMutateAsync).not.toHaveBeenCalled();
	});

	it("creates a game then adds it to the library", async () => {
		const { onClose } = renderModal();

		fireEvent.click(screen.getByRole("switch", { name: /create manually/i }));
		fireEvent.change(screen.getByPlaceholderText("Game title"), {
			target: { value: "My Game" },
		});
		fireEvent.change(screen.getByPlaceholderText("game-slug"), {
			target: { value: "my-game" },
		});
		selectPlatforms("PlayStation 5");

		fireEvent.click(screen.getByRole("button", { name: /add to library/i }));

		await waitFor(() => {
			expect(createMutateAsync).toHaveBeenCalledWith({
				title: "My Game",
				slug: "my-game",
				genres: undefined,
			});
		});
		expect(addMutateAsync).toHaveBeenCalledWith({
			gamePublicId: "created-game-1",
			platformIds: [2],
			status: "backlog",
			notes: undefined,
		});
		expect(onClose).toHaveBeenCalled();
	});
});
