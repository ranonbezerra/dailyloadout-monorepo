import { Button, Menu } from "@mantine/core";
import { IconChevronDown, IconMicrophone, IconPhoto, IconTextPlus } from "@tabler/icons-react";

interface QuickAddMenuProps {
	onText: () => void;
	onVoice: () => void;
	onPhoto: () => void;
}

export function QuickAddMenu({ onText, onVoice, onPhoto }: QuickAddMenuProps) {
	return (
		<Menu position="bottom-end" withinPortal>
			<Menu.Target>
				<Button rightSection={<IconChevronDown size={14} />}>Quick Add</Button>
			</Menu.Target>
			<Menu.Dropdown>
				<Menu.Item leftSection={<IconTextPlus size={16} />} onClick={onText}>
					Text
				</Menu.Item>
				<Menu.Item leftSection={<IconMicrophone size={16} />} onClick={onVoice}>
					Voice
				</Menu.Item>
				<Menu.Item leftSection={<IconPhoto size={16} />} onClick={onPhoto}>
					Photo
				</Menu.Item>
			</Menu.Dropdown>
		</Menu>
	);
}
