/**
 * Shared snake_case ↔ camelCase conversion utilities.
 *
 * The API returns snake_case JSON; the frontend uses camelCase.
 * These functions bridge the two conventions.
 */

function snakeToCamelKey(key: string): string {
	return key.replace(/_([a-z0-9])/g, (_, char: string) => char.toUpperCase());
}

export function snakeToCamel<T>(data: unknown): T {
	if (Array.isArray(data)) {
		return data.map((item) => snakeToCamel(item)) as T;
	}
	if (data !== null && typeof data === "object") {
		const converted: Record<string, unknown> = {};
		for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
			converted[snakeToCamelKey(key)] = snakeToCamel(value);
		}
		return converted as T;
	}
	return data as T;
}

function camelToSnakeKey(key: string): string {
	return key.replace(/[A-Z]/g, (char) => `_${char.toLowerCase()}`);
}

export function camelToSnake(data: Record<string, unknown>): Record<string, unknown> {
	const converted: Record<string, unknown> = {};
	for (const [key, value] of Object.entries(data)) {
		if (value !== undefined) {
			converted[camelToSnakeKey(key)] = value;
		}
	}
	return converted;
}
