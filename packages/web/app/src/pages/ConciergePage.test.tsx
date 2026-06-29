import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ConciergeEvent } from "../types/concierge";
import { ConciergePage } from "./ConciergePage";

const streamConcierge = vi.fn();
const fetchLibraryEntry = vi.fn();

vi.mock("../lib/concierge-api", () => ({
	streamConcierge: (...args: unknown[]) => streamConcierge(...args),
}));

vi.mock("../lib/library-api", async (importOriginal) => ({
	...(await importOriginal<typeof import("../lib/library-api")>()),
	fetchLibraryEntry: (...args: unknown[]) => fetchLibraryEntry(...args),
}));

async function* events(items: ConciergeEvent[]): AsyncGenerator<ConciergeEvent> {
	for (const item of items) yield item;
}

function renderPage() {
	const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
	return render(
		<QueryClientProvider client={client}>
			<MantineProvider>
				<MemoryRouter>
					<ConciergePage />
				</MemoryRouter>
			</MantineProvider>
		</QueryClientProvider>,
	);
}

afterEach(() => {
	streamConcierge.mockReset();
	fetchLibraryEntry.mockReset();
});

describe("ConciergePage", () => {
	it("renders the empty state prompt", () => {
		renderPage();
		expect(screen.getByText("What should you play tonight?")).toBeInTheDocument();
	});

	it("sends a message and shows the streamed reply", async () => {
		streamConcierge.mockReturnValue(
			events([{ token: "Try Hades." }, { done: true, thread_id: "t1" }]),
		);

		renderPage();
		const input = screen.getByPlaceholderText("Ask the concierge…");
		fireEvent.change(input, { target: { value: "something short" } });
		fireEvent.keyDown(input, { key: "Enter" });

		await waitFor(() => expect(screen.getByText("something short")).toBeInTheDocument());
		await waitFor(() => expect(screen.getByText("Try Hades.")).toBeInTheDocument());
		expect(streamConcierge).toHaveBeenCalledWith(
			"something short",
			undefined,
			expect.any(AbortSignal),
		);
	});

	it("renders a Play CTA for a validated recommendation", async () => {
		streamConcierge.mockReturnValue(
			events([
				{ token: "Give this a go." },
				{ recommendation: { id: "abc", title: "Hades" } },
				{ done: true, thread_id: "t1" },
			]),
		);

		renderPage();
		const input = screen.getByPlaceholderText("Ask the concierge…");
		fireEvent.change(input, { target: { value: "what should I play?" } });
		fireEvent.keyDown(input, { key: "Enter" });

		await waitFor(() =>
			expect(screen.getByRole("button", { name: /Play Hades/ })).toBeInTheDocument(),
		);
	});

	it("opens the recap-choice dialog when the Play CTA is clicked", async () => {
		streamConcierge.mockReturnValue(
			events([
				{ token: "Give this a go." },
				{ recommendation: { id: "entry-1", title: "Hades" } },
				{ done: true, thread_id: "t1" },
			]),
		);
		// The CTA fetches the full entry, then opens the recap modal for it.
		fetchLibraryEntry.mockResolvedValue({
			publicId: "entry-1",
			game: { title: "Hades" },
			platform: { id: 1, label: "PC" },
			status: "playing",
		});

		renderPage();
		const input = screen.getByPlaceholderText("Ask the concierge…");
		fireEvent.change(input, { target: { value: "what should I play?" } });
		fireEvent.keyDown(input, { key: "Enter" });

		const playButton = await screen.findByRole("button", { name: /Play Hades/ });
		fireEvent.click(playButton);

		// The recap-choice dialog opens for the recommended game.
		await waitFor(() => expect(fetchLibraryEntry).toHaveBeenCalledWith("entry-1"));
		await waitFor(() => expect(screen.getByText("Recap: Hades")).toBeInTheDocument());
		expect(screen.getByText(/Quick recap/)).toBeInTheDocument();
	});

	it("shows the typing indicator while the reply is pending", async () => {
		let release: () => void = () => {};
		const gate = new Promise<void>((resolve) => {
			release = resolve;
		});
		async function* gated(): AsyncGenerator<ConciergeEvent> {
			await gate;
			yield { token: "Done." };
			yield { done: true, thread_id: "t1" };
		}
		streamConcierge.mockReturnValue(gated());

		renderPage();
		const input = screen.getByPlaceholderText("Ask the concierge…");
		fireEvent.change(input, { target: { value: "hi" } });
		fireEvent.keyDown(input, { key: "Enter" });

		// Reply hasn't arrived yet → the animated typing indicator is visible.
		await waitFor(() =>
			expect(screen.getByLabelText("Concierge is thinking")).toBeInTheDocument(),
		);

		release();
		await waitFor(() => expect(screen.getByText("Done.")).toBeInTheDocument());
		expect(screen.queryByLabelText("Concierge is thinking")).not.toBeInTheDocument();
	});
});
