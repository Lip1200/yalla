/**
 * App.jsx smoke test — verifies the component imports and renders
 * (without auth session) the login screen instead of the dashboard.
 *
 * We mock global.fetch to return the demo fallback shape if anything
 * inside App tries to hit the network on mount.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import App from "../App";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      }),
    ),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("renders the login screen when no session is present", () => {
    render(<App />);
    // LoginScreen displays its own title; we assert anything that's
    // unique to the login UI rather than the dashboard.
    expect(screen.getByText(/Connexion/i)).toBeInTheDocument();
  });

  it("does not show the patient list when unauthenticated", () => {
    render(<App />);
    // 'Mes patients' is the dashboard heading — must be absent.
    expect(screen.queryByText(/Mes patients/i)).toBeNull();
  });
});
