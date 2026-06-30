import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AccountPage } from "./AccountPage";

vi.mock("./ChangePasswordPage", () => ({
	ChangePasswordPage: () => <div data-testid="change-password" />,
}));
vi.mock("./MfaSection", () => ({
	MfaSection: () => <div data-testid="mfa-section" />,
}));

describe("AccountPage", () => {
	it("renders the security heading and both sections", () => {
		render(
			<MantineProvider>
				<AccountPage />
			</MantineProvider>,
		);
		expect(screen.getByRole("heading", { name: /account security/i })).toBeInTheDocument();
		expect(screen.getByTestId("change-password")).toBeInTheDocument();
		expect(screen.getByTestId("mfa-section")).toBeInTheDocument();
	});
});
