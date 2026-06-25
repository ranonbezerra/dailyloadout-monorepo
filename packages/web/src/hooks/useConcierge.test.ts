import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ConciergeEvent } from "../types/concierge";
import { useConcierge } from "./useConcierge";

const streamConcierge = vi.fn();

vi.mock("../lib/concierge-api", () => ({
	streamConcierge: (...args: unknown[]) => streamConcierge(...args),
}));

async function* events(items: ConciergeEvent[]): AsyncGenerator<ConciergeEvent> {
	for (const item of items) yield item;
}

afterEach(() => {
	streamConcierge.mockReset();
});

describe("useConcierge", () => {
	it("appends the user message and streams the assistant reply token by token", async () => {
		streamConcierge.mockReturnValue(
			events([{ token: "Play " }, { token: "Hollow Knight." }, { done: true, thread_id: "t1" }]),
		);

		const { result } = renderHook(() => useConcierge());

		await act(async () => {
			await result.current.send("what should I play?");
		});

		expect(result.current.messages).toEqual([
			{ role: "user", text: "what should I play?" },
			{ role: "assistant", text: "Play Hollow Knight." },
		]);
		expect(result.current.isStreaming).toBe(false);
		expect(result.current.error).toBeNull();
	});

	it("attaches a validated recommendation and tracks the active tool", async () => {
		streamConcierge.mockReturnValue(
			events([
				{ tool: "search_library", phase: "start" },
				{ tool: "search_library", phase: "end" },
				{ token: "Give this a go." },
				{ recommendation: { id: "abc", title: "Hades" } },
				{ done: true, thread_id: "t1" },
			]),
		);

		const { result } = renderHook(() => useConcierge());
		await act(async () => {
			await result.current.send("what should I play?");
		});

		const last = result.current.messages.at(-1);
		expect(last?.text).toBe("Give this a go.");
		expect(last?.recommendation).toEqual({ id: "abc", title: "Hades" });
		expect(result.current.activeTool).toBeNull(); // cleared once the turn ends
	});

	it("appends a degrade nudge to the prose", async () => {
		streamConcierge.mockReturnValue(
			events([
				{ token: "Hmm." },
				{ degrade: "I'm not certain that one's in your library." },
				{ done: true, thread_id: "t1" },
			]),
		);

		const { result } = renderHook(() => useConcierge());
		await act(async () => {
			await result.current.send("play something");
		});

		expect(result.current.messages.at(-1)?.text).toContain("not certain");
	});

	it("threads the server thread_id into the next turn", async () => {
		streamConcierge
			.mockReturnValueOnce(events([{ token: "Hi." }, { done: true, thread_id: "thread-42" }]))
			.mockReturnValueOnce(events([{ token: "Again." }, { done: true, thread_id: "thread-42" }]));

		const { result } = renderHook(() => useConcierge());

		await act(async () => {
			await result.current.send("first");
		});
		await act(async () => {
			await result.current.send("second");
		});

		expect(streamConcierge).toHaveBeenNthCalledWith(
			1,
			"first",
			undefined,
			expect.any(AbortSignal),
		);
		expect(streamConcierge).toHaveBeenNthCalledWith(
			2,
			"second",
			"thread-42",
			expect.any(AbortSignal),
		);
	});

	it("ignores empty input", async () => {
		const { result } = renderHook(() => useConcierge());
		await act(async () => {
			await result.current.send("   ");
		});
		expect(result.current.messages).toEqual([]);
		expect(streamConcierge).not.toHaveBeenCalled();
	});

	it("cancelling mid-stream keeps the partial reply without an error", async () => {
		// Stream one token, then park until the abort signal fires (rejecting
		// like an aborted fetch would).
		streamConcierge.mockImplementation((_msg: string, _tid: undefined, signal: AbortSignal) =>
			(async function* () {
				yield { token: "partial " };
				await new Promise((_resolve, reject) => {
					signal.addEventListener("abort", () =>
						reject(Object.assign(new Error("aborted"), { name: "AbortError" })),
					);
				});
			})(),
		);

		const { result } = renderHook(() => useConcierge());
		let sendPromise: Promise<void> = Promise.resolve();
		await act(async () => {
			sendPromise = result.current.send("what should I play?");
			await Promise.resolve(); // let the first token flush
		});
		await act(async () => {
			result.current.cancel();
			await sendPromise;
		});

		expect(result.current.error).toBeNull();
		expect(result.current.isStreaming).toBe(false);
		expect(result.current.messages.at(-1)?.text).toContain("partial");
	});

	it("surfaces a server error event", async () => {
		streamConcierge.mockReturnValue(
			events([
				{ error: "The concierge is unavailable right now." },
				{ done: true, thread_id: "t1" },
			]),
		);

		const { result } = renderHook(() => useConcierge());
		await act(async () => {
			await result.current.send("hello");
		});

		expect(result.current.error).toBe("The concierge is unavailable right now.");
		expect(result.current.messages.at(-1)?.text).toContain("unavailable");
	});

	it("surfaces an error when the stream throws", async () => {
		streamConcierge.mockImplementation(() => {
			throw new Error("boom");
		});

		const { result } = renderHook(() => useConcierge());
		await act(async () => {
			await result.current.send("hello");
		});

		await waitFor(() => expect(result.current.error).not.toBeNull());
		const last = result.current.messages.at(-1);
		expect(last?.role).toBe("assistant");
		expect(last?.text).toContain("something went wrong");
	});
});
