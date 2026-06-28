import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ImageSourceModal } from "./ImageSourceModal";

function makeProps(overrides = {}) {
	return {
		opened: true,
		onClose: vi.fn(),
		onPhoto: vi.fn(),
		onScreenshots: vi.fn(),
		...overrides,
	};
}

function renderModal(props = makeProps()) {
	render(
		<MantineProvider>
			<ImageSourceModal {...props} />
		</MantineProvider>,
	);
	return props;
}

describe("ImageSourceModal", () => {
	beforeEach(() => vi.clearAllMocks());

	it("renders both source options when open", () => {
		renderModal();
		expect(screen.getByText("Photo of my shelf")).toBeInTheDocument();
		expect(screen.getByText("Library screenshot")).toBeInTheDocument();
	});

	it("choosing the photo option calls onPhoto and closes", () => {
		const props = renderModal();
		fireEvent.click(screen.getByTestId("image-source-photo"));
		expect(props.onPhoto).toHaveBeenCalledOnce();
		expect(props.onClose).toHaveBeenCalledOnce();
		expect(props.onScreenshots).not.toHaveBeenCalled();
	});

	it("choosing the screenshot option calls onScreenshots and closes", () => {
		const props = renderModal();
		fireEvent.click(screen.getByTestId("image-source-screenshots"));
		expect(props.onScreenshots).toHaveBeenCalledOnce();
		expect(props.onClose).toHaveBeenCalledOnce();
		expect(props.onPhoto).not.toHaveBeenCalled();
	});

	it("renders nothing when closed", () => {
		renderModal(makeProps({ opened: false }));
		expect(screen.queryByText("Photo of my shelf")).not.toBeInTheDocument();
	});
});
