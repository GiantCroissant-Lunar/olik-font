import type { AuthProvider } from "@refinedev/core";

/**
 * Solo-dev local posture: no authentication, no permission checks.
 * Plan 11+ can introduce a real auth provider if multi-user is added.
 */
export const noopAuthProvider: AuthProvider = {
  login: async () => ({ success: true }),
  logout: async () => ({ success: true }),
  check: async () => ({ authenticated: true }),
  onError: async () => ({}),
  getPermissions: async () => [],
  getIdentity: async () => ({ id: "local", name: "reviewer" }),
};
