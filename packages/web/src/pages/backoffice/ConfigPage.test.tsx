import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, type Mock, vi } from "vitest";
import type { ConfigEntry } from "../../types/backoffice";
import { ConfigPage } from "./ConfigPage";

vi.mock("../../hooks/useBackoffice", () => ({
	useConfig: vi.fn(),
	useConfigActions: vi.fn(),
}));
vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

import { useConfig, useConfigActions } from "../../hooks/useBackoffice";

const mockUseConfig = useConfig as Mock;
const mockUseConfigActions = useConfigActions as Mock;

function entry(over: Partial<ConfigEntry> = {}): ConfigEntry {
	return {
		key: "rate_limit_enabled",
		kind: "bool",
		category: "kill_switch",
		description: "Master switch for rate limiting.",
		effectiveValue: true,
		overrideValue: null,
		baselineValue: true,
		isOverridden: false,
		minValue: null,
		maxValue: null,
		updatedAt: null,
		updatedBy: null,
		...over,
	};
}

function renderPage() {
	return render(
		<MantineProvider>
			<ConfigPage />
		</MantineProvider>,
	);
}

describe("ConfigPage", () => {
	it("toggling a bool knob calls set with the new value", () => {
		const set = { mutate: vi.fn(), isPending: false };
		const clear = { mutate: vi.fn(), isPending: false };
		mockUseConfigActions.mockReturnValue({ set, clear });
		mockUseConfig.mockReturnValue({
			data: { items: [entry()] },
			isLoading: false,
			isError: false,
		});
		renderPage();

		fireEvent.click(screen.getByLabelText("Toggle rate_limit_enabled"));
		expect(set.mutate).toHaveBeenCalledWith(
			{ key: "rate_limit_enabled", value: false },
			expect.anything(),
		);
	});

	it("shows an override badge and a reset control for overridden keys", () => {
		const set = { mutate: vi.fn(), isPending: false };
		const clear = { mutate: vi.fn(), isPending: false };
		mockUseConfigActions.mockReturnValue({ set, clear });
		mockUseConfig.mockReturnValue({
			data: { items: [entry({ isOverridden: true, effectiveValue: false })] },
			isLoading: false,
			isError: false,
		});
		renderPage();

		expect(screen.getByText("override")).toBeInTheDocument();
		fireEvent.click(screen.getByLabelText("Reset rate_limit_enabled"));
		expect(clear.mutate).toHaveBeenCalledWith("rate_limit_enabled", expect.anything());
	});

	it("groups knobs by category", () => {
		mockUseConfigActions.mockReturnValue({
			set: { mutate: vi.fn(), isPending: false },
			clear: { mutate: vi.fn(), isPending: false },
		});
		mockUseConfig.mockReturnValue({
			data: {
				items: [
					entry(),
					entry({
						key: "cost_user_per_day",
						kind: "int",
						category: "cap",
						effectiveValue: 200,
						baselineValue: 200,
						minValue: 0,
						maxValue: 1000,
					}),
				],
			},
			isLoading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getByText("Kill-switches")).toBeInTheDocument();
		expect(screen.getByText("Abuse caps")).toBeInTheDocument();
	});
});
