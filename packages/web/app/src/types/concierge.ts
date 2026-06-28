export type ChatRole = "user" | "assistant";

export interface Recommendation {
	id: string;
	title: string;
}

export interface ChatMessage {
	role: ChatRole;
	text: string;
	// A validated pick surfaced by the server (Epic 16) — rendered as a CTA.
	recommendation?: Recommendation;
}

// One Server-Sent Event from POST /v1/concierge/chat (ROADMAP Epic 16).
export interface ConciergeEvent {
	token?: string; // a chunk of prose to append live
	tool?: string; // a tool call name (paired with `phase`)
	phase?: "start" | "end";
	recommendation?: Recommendation; // a validated game pick
	degrade?: string; // the pick failed the library guard; a clarifying nudge
	error?: string;
	done?: boolean;
	thread_id?: string;
}
