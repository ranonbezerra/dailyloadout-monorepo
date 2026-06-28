import { fetchWithAuthRetry } from "@dl/shared/api";
import type { ConciergeEvent } from "../types/concierge";

// ---------------------------------------------------------------------------
// Backlog Concierge chat — consumes the SSE endpoint as an async generator
// (ROADMAP Epic 16). The endpoint streams typed events as the turn generates:
// `token` (prose), `tool` (+`phase`), `recommendation`, `degrade`, `error`,
// then a final `done` carrying the `thread_id` for the next turn.
// ---------------------------------------------------------------------------

export async function* streamConcierge(
	message: string,
	threadId?: string,
	signal?: AbortSignal,
): AsyncGenerator<ConciergeEvent> {
	const res = await fetchWithAuthRetry("/v1/concierge/chat", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ message, thread_id: threadId }),
		signal,
	});

	if (!res.ok) {
		throw new Error(`Concierge request failed (${res.status})`);
	}
	if (!res.body) {
		throw new Error("Concierge response had no body");
	}

	const reader = res.body.getReader();
	const decoder = new TextDecoder();
	let buffer = "";

	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			buffer += decoder.decode(value, { stream: true });
			// SSE events are separated by a blank line; process complete lines.
			const lines = buffer.split("\n");
			buffer = lines.pop() ?? "";

			for (const line of lines) {
				const trimmed = line.trim();
				if (!trimmed.startsWith("data:")) continue;
				const payload = trimmed.slice("data:".length).trim();
				if (!payload) continue;
				try {
					yield JSON.parse(payload) as ConciergeEvent;
				} catch {
					// Skip malformed events rather than aborting the stream.
				}
			}
		}
	} finally {
		reader.releaseLock();
	}
}
