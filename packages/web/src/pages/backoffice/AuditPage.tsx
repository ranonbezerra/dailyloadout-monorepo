import {
	Card,
	Center,
	Code,
	Group,
	Loader,
	Pagination,
	Stack,
	Table,
	Text,
	Title,
} from "@mantine/core";
import { useState } from "react";
import { useAudit } from "../../hooks/useBackoffice";
import { ActionLabel, relativeTime } from "./shared";

const PAGE_SIZE = 25;

export function AuditPage() {
	const [page, setPage] = useState(1);
	const { data, isLoading, isError } = useAudit({
		limit: PAGE_SIZE,
		offset: (page - 1) * PAGE_SIZE,
	});

	const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

	return (
		<Stack gap="lg">
			<div>
				<Title order={2}>Audit log</Title>
				<Text c="dimmed" size="sm">
					Every backoffice mutation, newest first.
				</Text>
			</div>

			<Card padding={0}>
				{isLoading ? (
					<Center py="xl">
						<Loader color="violet" />
					</Center>
				) : isError ? (
					<Center py="xl">
						<Text c="red">Failed to load the audit log.</Text>
					</Center>
				) : !data || data.items.length === 0 ? (
					<Center py="xl">
						<Text c="dimmed">No admin actions recorded yet.</Text>
					</Center>
				) : (
					<Table.ScrollContainer minWidth={680}>
						<Table verticalSpacing="sm" highlightOnHover>
							<Table.Thead>
								<Table.Tr>
									<Table.Th>Action</Table.Th>
									<Table.Th>By</Table.Th>
									<Table.Th>Target</Table.Th>
									<Table.Th>Detail</Table.Th>
									<Table.Th>When</Table.Th>
								</Table.Tr>
							</Table.Thead>
							<Table.Tbody>
								{data.items.map((a) => (
									<Table.Tr
										key={`${a.createdAt}-${a.action}-${a.targetEmail ?? ""}-${a.detail ?? ""}`}
									>
										<Table.Td>
											<ActionLabel action={a.action} />
										</Table.Td>
										<Table.Td>
											<Text size="sm">{a.adminEmail ?? "—"}</Text>
										</Table.Td>
										<Table.Td>
											<Text size="sm" c="dimmed">
												{a.targetEmail ?? "—"}
											</Text>
										</Table.Td>
										<Table.Td>
											{a.detail ? (
												<Code>{a.detail}</Code>
											) : (
												<Text size="sm" c="dimmed">
													—
												</Text>
											)}
										</Table.Td>
										<Table.Td>
											<Text size="sm" c="dimmed">
												{relativeTime(a.createdAt)}
											</Text>
										</Table.Td>
									</Table.Tr>
								))}
							</Table.Tbody>
						</Table>
					</Table.ScrollContainer>
				)}
			</Card>

			{data && data.total > PAGE_SIZE && (
				<Group justify="space-between">
					<Text size="xs" c="dimmed">
						{data.total} entries
					</Text>
					<Pagination color="violet" value={page} onChange={setPage} total={totalPages} />
				</Group>
			)}
		</Stack>
	);
}
