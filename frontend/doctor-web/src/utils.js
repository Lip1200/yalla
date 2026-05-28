/**
 * Pure helpers extracted from App.jsx so they're unit-testable in
 * isolation (no react-native-web, no state, no JSX).
 */

export function formatMonth(value) {
  return new Intl.DateTimeFormat("fr-FR", { month: "short" }).format(new Date(value));
}

export function formatDate(value) {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function buildDisplayedDoctor(session, fallbackDoctor) {
  const user = session?.user ?? {};
  const emailName = user.email ? user.email.split("@")[0].replace(/[._-]+/g, " ") : "";
  const formattedEmailName = emailName
    ? `Dr. ${emailName.replace(/\b\w/g, (letter) => letter.toUpperCase())}`
    : null;

  return {
    full_name:
      user.full_name ||
      formattedEmailName ||
      fallbackDoctor?.full_name ||
      "Médecin connecté",
    specialty:
      user.specialty ||
      (user.email ? "Spécialité non renseignée" : fallbackDoctor?.specialty) ||
      "Spécialité non renseignée",
    facility:
      user.facility ||
      (user.email ? "Établissement non renseigné" : fallbackDoctor?.facility) ||
      "Établissement non renseigné",
  };
}

/**
 * Filter logic mirrored from App.jsx's patient list. Pulled out so we
 * can unit-test the predicate without rendering React.
 *
 * `filter` ∈ { "all" | "expert" | "with_app" }
 * `query` is matched (case-insensitive) against full_name and
 * primary_goal.
 */
export function filterPatients(patients, filter, query) {
  const normalised = (query || "").trim().toLowerCase();
  return patients.filter((patient) => {
    if (filter === "expert" && !patient.is_expert_patient) return false;
    if (filter === "with_app" && !patient.has_app_access) return false;
    if (!normalised) return true;
    const haystack = [
      patient.full_name,
      patient.primary_goal,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(normalised);
  });
}

/**
 * Extract the bare token from an invitation_url returned by
 * POST /api/doctors/{id}/patients/accounts. The patient-app's
 * SetupAccountScreen accepts either form, but the doctor-web UI now
 * shows just the token (the URL itself routes to doctor-web — useless
 * on a phone). See feat/expo-dev-build commit "doctor-web: show
 * invitation token (not URL)".
 */
export function extractInvitationToken(invitationUrl) {
  if (!invitationUrl) return "";
  const fromQuery = invitationUrl.split("token=").pop();
  return fromQuery || "";
}
