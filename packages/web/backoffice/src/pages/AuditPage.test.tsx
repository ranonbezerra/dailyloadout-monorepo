import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, type Mock, vi } from "vitest";
import type { AuditEntry } from "../types/backoffice";
import { AuditPage } from "./AuditPage";

vi.mock("../hooks/useBackoffice", () => ({
	useAudit: vi.fn(),
}));

import { useAudit } from "../hooks/useBackoffice";

const mockUseAudit = useAudit as Mock;

function entry(over: Partial<AuditEntry> = {}): AuditEntry {
	return {
		action: "config.set",
		detail: "cost_user_per_day = 42",
		createdAt: new Date().toISOString(),
		adminPublicId: "a1",
		adminEmail: "boss@x.com",
		targetPublicId: null,
		targetEmail: null,
		...over,
	};
}

function renderPage() {
	return render(
		<MantineProvider>
			<AuditPage />
		</MantineProvider>,
	);
}

describe("AuditPage", () => {
	it("renders audit rows with action and detail", () => {
		mockUseAudit.mockReturnValue({
			data: { items: [entry()], total: 1, limit: 25, offset: 0 },
			isLoading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getByText("Config set")).toBeInTheDocument();
		expect(screen.getByText("cost_user_per_day = 42")).toBeInTheDocument();
		expect(screen.getByText("boss@x.com")).toBeInTheDocument();
	});

	it("shows an empty state when there are no entries", () => {
		mockUseAudit.mockReturnValue({
			data: { items: [], total: 0, limit: 25, offset: 0 },
			isLoading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getByText("No admin actions recorded yet.")).toBeInTheDocument();
	});
});
