import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Distinct dev port from the player app (web runs on 5173) so both can run side
// by side against the same API.
export default defineConfig({
	plugins: [react()],
	server: { port: 5174 },
});
