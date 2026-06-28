import { describe, expect, it } from "vitest";
import { camelToSnake, snakeToCamel } from "./case-convert";

// ---------------------------------------------------------------------------
// snakeToCamel
// ---------------------------------------------------------------------------

describe("snakeToCamel", () => {
	it("converts a flat snake_case object to camelCase", () => {
		const input = { first_name: "Ada", last_name: "Lovelace", age: 36 };
		expect(snakeToCamel(input)).toEqual({
			firstName: "Ada",
			lastName: "Lovelace",
			age: 36,
		});
	});

	it("converts nested objects recursively", () => {
		const input = {
			user_profile: {
				first_name: "Grace",
				home_address: {
					zip_code: "90210",
					street_name: "Main St",
				},
			},
		};
		expect(snakeToCamel(input)).toEqual({
			userProfile: {
				firstName: "Grace",
				homeAddress: {
					zipCode: "90210",
					streetName: "Main St",
				},
			},
		});
	});

	it("converts arrays of objects", () => {
		const input = [
			{ item_name: "Sword", item_id: 1 },
			{ item_name: "Shield", item_id: 2 },
		];
		expect(snakeToCamel(input)).toEqual([
			{ itemName: "Sword", itemId: 1 },
			{ itemName: "Shield", itemId: 2 },
		]);
	});

	it("converts arrays nested inside objects", () => {
		const input = {
			load_items: [{ item_name: "Boots" }, { item_name: "Helmet" }],
		};
		expect(snakeToCamel(input)).toEqual({
			loadItems: [{ itemName: "Boots" }, { itemName: "Helmet" }],
		});
	});

	it("returns null as-is", () => {
		expect(snakeToCamel(null)).toBeNull();
	});

	it("returns primitives as-is", () => {
		expect(snakeToCamel(42)).toBe(42);
		expect(snakeToCamel("hello_world")).toBe("hello_world");
		expect(snakeToCamel(true)).toBe(true);
		expect(snakeToCamel(undefined)).toBeUndefined();
	});

	it("returns an empty object for an empty object", () => {
		expect(snakeToCamel({})).toEqual({});
	});

	it("returns an empty array for an empty array", () => {
		expect(snakeToCamel([])).toEqual([]);
	});

	it("handles keys with consecutive underscores gracefully", () => {
		const input = { some__double_key: "val" };
		// Only underscores followed by [a-z0-9] are converted; the lone
		// underscore from the double stays.
		const result = snakeToCamel<Record<string, string>>(input);
		expect(result).toHaveProperty("some_DoubleKey");
	});

	it("handles keys with digits after underscores", () => {
		const input = { item_2_count: 5 };
		expect(snakeToCamel(input)).toEqual({ item2Count: 5 });
	});

	it("leaves already-camelCase keys unchanged", () => {
		const input = { firstName: "Ada" };
		expect(snakeToCamel(input)).toEqual({ firstName: "Ada" });
	});
});

// ---------------------------------------------------------------------------
// camelToSnake
// ---------------------------------------------------------------------------

describe("camelToSnake", () => {
	it("converts a flat camelCase object to snake_case", () => {
		const input = { firstName: "Ada", lastName: "Lovelace", age: 36 };
		expect(camelToSnake(input)).toEqual({
			first_name: "Ada",
			last_name: "Lovelace",
			age: 36,
		});
	});

	it("filters out undefined values", () => {
		const input = {
			firstName: "Ada",
			lastName: undefined,
			age: 36,
		};
		expect(camelToSnake(input)).toEqual({
			first_name: "Ada",
			age: 36,
		});
	});

	it("keeps null values (only undefined is filtered)", () => {
		const input = { firstName: "Ada", middleName: null };
		expect(camelToSnake(input)).toEqual({
			first_name: "Ada",
			middle_name: null,
		});
	});

	it("keeps falsy values that are not undefined", () => {
		const input = { isActive: false, count: 0, label: "" };
		expect(camelToSnake(input)).toEqual({
			is_active: false,
			count: 0,
			label: "",
		});
	});

	it("returns an empty object for an empty object", () => {
		expect(camelToSnake({})).toEqual({});
	});

	it("returns an empty object when all values are undefined", () => {
		expect(camelToSnake({ a: undefined, b: undefined })).toEqual({});
	});

	it("does not recursively convert nested objects", () => {
		// camelToSnake is shallow by design
		const input = { outerKey: { innerKey: "val" } };
		const result = camelToSnake(input);
		expect(result).toEqual({ outer_key: { innerKey: "val" } });
	});

	it("leaves already-snake_case keys unchanged", () => {
		const input = { first_name: "Ada" };
		expect(camelToSnake(input)).toEqual({ first_name: "Ada" });
	});
});

// ---------------------------------------------------------------------------
// Round-trip
// ---------------------------------------------------------------------------

describe("round-trip conversion", () => {
	it("snakeToCamel -> camelToSnake produces original keys for a flat object", () => {
		const original = { first_name: "Ada", last_name: "Lovelace" };
		const camel = snakeToCamel<Record<string, unknown>>(original);
		const backToSnake = camelToSnake(camel);
		expect(backToSnake).toEqual(original);
	});

	it("camelToSnake -> snakeToCamel produces original keys for a flat object", () => {
		const original = { firstName: "Ada", lastName: "Lovelace" };
		const snake = camelToSnake(original);
		const backToCamel = snakeToCamel<Record<string, unknown>>(snake);
		expect(backToCamel).toEqual(original);
	});
});
