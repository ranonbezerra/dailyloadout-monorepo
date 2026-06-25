import { useCallback, useRef, useState } from "react";
import { streamConcierge } from "../lib/concierge-api";
import type { ChatMessage, Recommendation } from "../types/concierge";

// ---------------------------------------------------------------------------
// useConcierge — drives a streaming chat conversation with the Backlog
// Concierge (ROADMAP Epic 16). Renders prose token-by-token, surfaces the
// active tool call as an affordance, attaches a validated recommendation, and
// can cancel a turn mid-stream. Threads the server-issued thread_id across turns.
// ---------------------------------------------------------------------------

const FALLBACK_ERROR = "Sorry, something went wrong. Please try again.";

export function useConcierge() {
	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const [isStreaming, setIsStreaming] = useState(false);
	const [activeTool, setActiveTool] = useState<string | null>(null);
	const [error, setError] = useState<string | null>(null);
	const threadId = useRef<string | undefined>(undefined);
	const abortRef = useRef<AbortController | null>(null);

	const cancel = useCallback(() => {
		abortRef.current?.abort();
	}, []);

	const send = useCallback(
		async (raw: string) => {
			const text = raw.trim();
			if (!text || isStreaming) return;

			setError(null);
			setIsStreaming(true);
			setActiveTool(null);
			// Append the user message + an empty assistant placeholder to fill in.
			setMessages((prev) => [...prev, { role: "user", text }, { role: "assistant", text: "" }]);

			const patchAssistant = (patch: (last: ChatMessage) => ChatMessage) => {
				setMessages((prev) => {
					const next = [...prev];
					next[next.length - 1] = patch(next[next.length - 1]);
					return next;
				});
			};
			const appendToken = (token: string) =>
				patchAssistant((last) => ({ ...last, text: last.text + token }));
			const setRecommendation = (rec: Recommendation) =>
				patchAssistant((last) => ({ ...last, recommendation: rec }));

			const controller = new AbortController();
			abortRef.current = controller;

			try {
				for await (const event of streamConcierge(text, threadId.current, controller.signal)) {
					if (event.error) {
						setError(event.error);
						patchAssistant((last) => ({ ...last, text: event.error ?? FALLBACK_ERROR }));
					}
					if (event.token) appendToken(event.token);
					if (event.tool) setActiveTool(event.phase === "end" ? null : event.tool);
					if (event.recommendation) setRecommendation(event.recommendation);
					if (event.degrade) appendToken(`\n\n${event.degrade}`);
					if (event.done && event.thread_id) threadId.current = event.thread_id;
				}
			} catch {
				// A user-initiated cancel surfaces as an abort — keep the partial
				// reply and don't show an error. Anything else is a real failure.
				if (!controller.signal.aborted) {
					setError(FALLBACK_ERROR);
					patchAssistant((last) => ({ ...last, text: last.text || FALLBACK_ERROR }));
				}
			} finally {
				abortRef.current = null;
				setActiveTool(null);
				setIsStreaming(false);
			}
		},
		[isStreaming],
	);

	return { messages, isStreaming, activeTool, error, send, cancel } as const;
}
