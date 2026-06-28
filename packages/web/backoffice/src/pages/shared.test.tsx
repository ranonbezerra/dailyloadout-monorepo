import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ActionLabel, relativeTime } from "./shared";

describe("relativeTime", () => {
	const now = Date.now();
	it("formats recent times", () => {
		expect(relativeTime(new Date(now - 5_000).toISOString())).toBe("just now");
		expect(relativeTime(new Date(now - 5 * 60_000).toISOString())).toBe("5m ago");
		expect(relativeTime(new Date(now - 3 * 3_600_000).toISOString())).toBe("3h ago");
		expect(relativeTime(new Date(now - 2 * 86_400_000).toISOString())).toBe("2d ago");
	});

	it("falls back to a date for old timestamps and invalid input", () => {
		const old = new Date(now - 60 * 86_400_000).toISOString();
		expect(relativeTime(old)).toMatch(/\d/);
		expect(relativeTime("not-a-date")).toBe("not-a-date");
	});
});

describe("ActionLabel", () => {
	it("renders a known action and falls back for unknown ones", () => {
		render(
			<MantineProvider>
				<ActionLabel action="user.ban" />
				<ActionLabel action="mystery.action" />
			</MantineProvider>,
		);
		expect(screen.getByText("Ban")).toBeInTheDocument();
		expect(screen.getByText("mystery.action")).toBeInTheDocument();
	});
});
