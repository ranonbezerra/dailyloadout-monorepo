// Shared frontend code used by both the player app and the backoffice.
// The API client (cookie auth + silent refresh) and the snake/camel converters
// are identical across apps, so they live here once.
export * from "./api";
export * from "./case-convert";
