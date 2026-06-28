import { Button, Menu } from "@mantine/core";
import {
	IconChevronDown,
	IconForms,
	IconMicrophone,
	IconPhoto,
	IconSparkles,
} from "@tabler/icons-react";

interface QuickAddMenuProps {
	/** Manual form: fill in title, platform, status, genres, and notes. */
	onManual: () => void;
	/** Free-text description parsed by AI (e.g. "got Hollow Knight on Switch"). */
	onText: () => void;
	onVoice: () => void;
	/** A photo of a shelf or a library screenshot — disambiguated in a chooser. */
	onImage: () => void;
}

export function QuickAddMenu({ onManual, onText, onVoice, onImage }: QuickAddMenuProps) {
	return (
		<Menu position="bottom-end" withinPortal>
			<Menu.Target>
				<Button rightSection={<IconChevronDown size={14} />}>Quick Add</Button>
			</Menu.Target>
			<Menu.Dropdown>
				<Menu.Item leftSection={<IconForms size={16} />} onClick={onManual}>
					Add manually
				</Menu.Item>

				<Menu.Divider />
				{/* All of these run AI extraction and can pull in one or many games. */}
				<Menu.Label>Capture with AI</Menu.Label>
				<Menu.Item leftSection={<IconSparkles size={16} />} onClick={onText}>
					Describe in text
				</Menu.Item>
				<Menu.Item leftSection={<IconMicrophone size={16} />} onClick={onVoice}>
					Voice
				</Menu.Item>
				<Menu.Item leftSection={<IconPhoto size={16} />} onClick={onImage}>
					Photo or screenshot
				</Menu.Item>
			</Menu.Dropdown>
		</Menu>
	);
}
