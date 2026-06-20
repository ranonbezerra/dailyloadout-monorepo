import { Button, Code, Stack, Text, Title } from "@mantine/core";
import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
	children: ReactNode;
}

interface State {
	error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
	constructor(props: Props) {
		super(props);
		this.state = { error: null };
	}

	static getDerivedStateFromError(error: Error): State {
		return { error };
	}

	componentDidCatch(error: Error, info: ErrorInfo) {
		console.error("ErrorBoundary caught:", error, info.componentStack);
	}

	render() {
		if (this.state.error) {
			return (
				<Stack p="xl" maw={600} mx="auto" mt="xl">
					<Title order={3} c="red">
						Something went wrong
					</Title>
					<Text size="sm">{this.state.error.message}</Text>
					<Code block>{this.state.error.stack}</Code>
					<Button onClick={() => this.setState({ error: null })}>Try again</Button>
				</Stack>
			);
		}
		return this.props.children;
	}
}
