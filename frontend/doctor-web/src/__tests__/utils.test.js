import { describe, expect, it } from "vitest";

import {
  buildDisplayedDoctor,
  extractInvitationToken,
  filterPatients,
  formatDate,
  formatMonth,
} from "../utils";

describe("formatDate / formatMonth", () => {
  it("formats an ISO date in fr-FR with day/month/year", () => {
    const formatted = formatDate("2026-05-21");
    expect(formatted).toMatch(/21/);
    expect(formatted).toMatch(/2026/);
  });

  it("formats month only", () => {
    const formatted = formatMonth("2026-05-21");
    // Just assert non-empty string in French locale.
    expect(formatted.length).toBeGreaterThan(0);
  });
});

describe("buildDisplayedDoctor", () => {
  it("returns fallback values when session is missing", () => {
    const out = buildDisplayedDoctor(null, null);
    expect(out.full_name).toBe("Médecin connecté");
    expect(out.specialty).toBe("Spécialité non renseignée");
    expect(out.facility).toBe("Établissement non renseigné");
  });

  it("derives a name from the email when full_name is absent", () => {
    const out = buildDisplayedDoctor(
      { user: { email: "nadia.benali@hug.ch" } },
      null,
    );
    expect(out.full_name).toBe("Dr. Nadia Benali");
  });

  it("prefers user.full_name when set", () => {
    const out = buildDisplayedDoctor(
      { user: { full_name: "Dr. Karim", email: "k@x.com" } },
      null,
    );
    expect(out.full_name).toBe("Dr. Karim");
  });

  it("falls back to fallbackDoctor when session is absent", () => {
    const out = buildDisplayedDoctor(null, {
      full_name: "Dr. Demo",
      specialty: "Endocrinologie",
      facility: "Clinique X",
    });
    expect(out.full_name).toBe("Dr. Demo");
    expect(out.specialty).toBe("Endocrinologie");
  });

  it("session with email but no specialty falls back to generic placeholder", () => {
    const out = buildDisplayedDoctor(
      { user: { email: "x@y.com" } },
      { specialty: "Cardio" },
    );
    // When the user is logged-in via email but never filled specialty
    // we show the generic placeholder, NOT the fallback (mirrors the
    // production behaviour that only kicks in when fully logged out).
    expect(out.specialty).toBe("Spécialité non renseignée");
  });
});

describe("filterPatients", () => {
  const patients = [
    {
      id: 1,
      full_name: "Karim El Mansouri",
      primary_goal: "Marcher 30 min par jour",
      has_app_access: true,
      is_expert_patient: false,
    },
    {
      id: 2,
      full_name: "Amina Saidi",
      primary_goal: "Animer le groupe marche",
      has_app_access: true,
      is_expert_patient: true,
    },
    {
      id: 3,
      full_name: "Youssef Haddad",
      primary_goal: "Réduire la sédentarité",
      has_app_access: false,
      is_expert_patient: false,
    },
  ];

  it("returns all when filter='all' and query empty", () => {
    expect(filterPatients(patients, "all", "")).toHaveLength(3);
  });

  it("filters to expert patients only", () => {
    const result = filterPatients(patients, "expert", "");
    expect(result.map((p) => p.id)).toEqual([2]);
  });

  it("filters to patients with app access", () => {
    const result = filterPatients(patients, "with_app", "");
    expect(result.map((p) => p.id).sort()).toEqual([1, 2]);
  });

  it("matches name (case-insensitive)", () => {
    const result = filterPatients(patients, "all", "AMINA");
    expect(result.map((p) => p.id)).toEqual([2]);
  });

  it("matches primary_goal", () => {
    const result = filterPatients(patients, "all", "sédentarité");
    expect(result.map((p) => p.id)).toEqual([3]);
  });

  it("combines filter and query (AND)", () => {
    // Expert + query that only matches expert → 1 result
    expect(filterPatients(patients, "expert", "marche")).toHaveLength(1);
    // Expert + query that matches a non-expert → 0 results
    expect(filterPatients(patients, "expert", "Karim")).toHaveLength(0);
  });
});

describe("extractInvitationToken", () => {
  it("pulls the bare token out of an invitation URL", () => {
    const token = extractInvitationToken(
      "https://yalla.example/setup?token=SECRETTOKEN123",
    );
    expect(token).toBe("SECRETTOKEN123");
  });

  it("returns the bare string if there is no token= prefix", () => {
    expect(extractInvitationToken("ABCXYZ")).toBe("ABCXYZ");
  });

  it("returns empty string for null/undefined", () => {
    expect(extractInvitationToken(null)).toBe("");
    expect(extractInvitationToken(undefined)).toBe("");
  });
});
