import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
  useWindowDimensions,
} from "react-native";
import {
  Activity,
  ClipboardList,
  Target,
  Trash2,
  Eye,
  LogOut,
  Plus,
  Search,
  Save,
  ShieldCheck,
  TrendingDown,
  UserCheck,
  Users,
  X,
} from "lucide-react";

import LoginScreen from "./LoginScreen";
import YALLA_LOGO from "./assets/yalla-logo.png";
import { API_BASE_URL, authFetch, clearSession, getSession, logout as logoutSession } from "./auth";

const DOCTOR_ID = 1;

export default function App() {
  const { width } = useWindowDimensions();
  const [session, setSession] = useState(() => getSession());
  const [dashboard, setDashboard] = useState(null);
  const [selectedPatientId, setSelectedPatientId] = useState(null);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [profilePatient, setProfilePatient] = useState(null);
  const [noteDraft, setNoteDraft] = useState("");
  const [patientSearch, setPatientSearch] = useState("");
  const [patientFilter, setPatientFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [savingNote, setSavingNote] = useState(false);
  const [error, setError] = useState("");
  const [challengeTemplates, setChallengeTemplates] = useState([]);
  const [patientAssignments, setPatientAssignments] = useState([]);
  const [assigningChallengeId, setAssigningChallengeId] = useState(null);
  const [challengeError, setChallengeError] = useState("");
  const [patientAccountForm, setPatientAccountForm] = useState({
    fullName: "",
    email: "",
    age: "45",
    primaryGoal: "Démarrer le suivi Yalla",
  });
  const [creatingPatientAccount, setCreatingPatientAccount] = useState(false);
  const [patientAccountResult, setPatientAccountResult] = useState(null);
  const [patientAccountError, setPatientAccountError] = useState("");

  async function handleLogout() {
    try {
      await logoutSession();
    } catch {
      clearSession();
    }
    setSession(null);
    setDashboard(null);
    setSelectedPatient(null);
    setProfilePatient(null);
  }

  const isCompact = width < 920;
  const patients = dashboard?.patients ?? [];
  const filteredPatients = useMemo(() => {
    const normalizedSearch = patientSearch.trim().toLowerCase();

    return patients.filter((patient) => {
      const matchesSearch =
        normalizedSearch.length === 0 ||
        patient.full_name.toLowerCase().includes(normalizedSearch) ||
        patient.primary_goal.toLowerCase().includes(normalizedSearch) ||
        patient.progress.status.toLowerCase().includes(normalizedSearch);

      const matchesFilter =
        patientFilter === "all" ||
        (patientFilter === "access" && patient.has_app_access) ||
        (patientFilter === "expert" && patient.is_expert_patient) ||
        (patientFilter === "review" && patient.progress.status === "À revoir");

      return matchesSearch && matchesFilter;
    });
  }, [patientFilter, patientSearch, patients]);

  useEffect(() => {
    if (session) {
      loadDashboard();
    } else {
      setLoading(false);
    }
  }, [session]);

  useEffect(() => {
    if (patients.length > 0 && selectedPatientId === null) {
      setSelectedPatientId(patients[0].id);
    }
  }, [patients, selectedPatientId]);

  useEffect(() => {
    if (selectedPatientId !== null) {
      loadPatient(selectedPatientId);
    }
  }, [selectedPatientId]);

  const reviewPatients = useMemo(
    () => patients.filter((patient) => patient.progress.status === "À revoir"),
    [patients],
  );
  const displayedDoctor = useMemo(() => buildDisplayedDoctor(session, dashboard?.doctor), [session, dashboard]);

  async function loadDashboard() {
    setLoading(true);
    setError("");

    try {
      const response = await authFetch(`${API_BASE_URL}/api/doctors/${DOCTOR_ID}/dashboard`);
      if (!response.ok) {
        throw new Error("Impossible de charger le tableau de bord médecin.");
      }

      const data = await response.json();
      setDashboard(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadPatient(patientId) {
    setDetailLoading(true);
    setError("");

    try {
      const response = await authFetch(`${API_BASE_URL}/api/doctors/${DOCTOR_ID}/patients/${patientId}`);
      if (!response.ok) {
        throw new Error("Impossible de charger le dossier patient.");
      }

      const data = await response.json();
      setSelectedPatient(data);
      if (profilePatient?.id === data.id) {
        setProfilePatient(data);
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setDetailLoading(false);
    }
  }

  async function createPatientAccount() {
    setPatientAccountError("");
    setPatientAccountResult(null);

    if (!patientAccountForm.email.trim() || !patientAccountForm.fullName.trim()) {
      setPatientAccountError("Nom complet et email patient sont requis.");
      return;
    }

    setCreatingPatientAccount(true);
    try {
      const response = await authFetch(`${API_BASE_URL}/api/doctors/${DOCTOR_ID}/patients/accounts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: patientAccountForm.email.trim(),
          full_name: patientAccountForm.fullName.trim(),
          age: Number(patientAccountForm.age) || 45,
          primary_goal: patientAccountForm.primaryGoal.trim() || "Démarrer le suivi Yalla",
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(body.detail ?? "Impossible de créer le compte patient.");
      }

      setPatientAccountResult(body);
      setPatientAccountForm({
        fullName: "",
        email: "",
        age: "45",
        primaryGoal: "Démarrer le suivi Yalla",
      });
      await loadDashboard();
      setSelectedPatientId(body.patient.id);
    } catch (requestError) {
      setPatientAccountError(requestError.message);
    } finally {
      setCreatingPatientAccount(false);
    }
  }

  async function openPatientProfile(patientId) {
    setSelectedPatientId(patientId);
    setError("");

    try {
      const response = await authFetch(`${API_BASE_URL}/api/doctors/${DOCTOR_ID}/patients/${patientId}`);
      if (!response.ok) {
        throw new Error("Impossible d'ouvrir la fiche patient.");
      }

      const data = await response.json();
      setSelectedPatient(data);
      setProfilePatient(data);
      setNoteDraft("");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function patchPatient(patientId, endpoint, payload) {
    setError("");

    try {
      const response = await authFetch(`${API_BASE_URL}/api/doctors/${DOCTOR_ID}/patients/${patientId}/${endpoint}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Action impossible pour ce patient.");
      }

      const updatedPatient = await response.json();
      await loadDashboard();
      setSelectedPatient(updatedPatient);
      setProfilePatient((current) => (current?.id === updatedPatient.id ? updatedPatient : current));
      setSelectedPatientId(updatedPatient.id);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function saveDoctorNote(patientId) {
    const content = noteDraft.trim();
    if (!content) {
      setError("La note ne peut pas être vide.");
      return;
    }

    setSavingNote(true);
    setError("");

    try {
      const response = await authFetch(`${API_BASE_URL}/api/doctors/${DOCTOR_ID}/patients/${patientId}/notes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Impossible d'enregistrer la note.");
      }

      const updatedPatient = await response.json();
      setSelectedPatient(updatedPatient);
      setProfilePatient(updatedPatient);
      setNoteDraft("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingNote(false);
    }
  }

  async function deleteDoctorNote(patientId, noteIndex) {
    setError("");

    try {
      const response = await authFetch(`${API_BASE_URL}/api/doctors/${DOCTOR_ID}/patients/${patientId}/notes/${noteIndex}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Impossible d'effacer la note.");
      }

      const updatedPatient = await response.json();
      setSelectedPatient(updatedPatient);
      setProfilePatient((current) => (current?.id === updatedPatient.id ? updatedPatient : current));
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function loadChallengeTemplates() {
    try {
      const response = await authFetch(`${API_BASE_URL}/api/challenges/?templates_only=true`);
      if (!response.ok) return;
      const data = await response.json();
      setChallengeTemplates(data);
    } catch {
      // Silent — templates section just stays empty if endpoint not ready
    }
  }

  async function loadPatientAssignments(patientId) {
    setChallengeError("");
    try {
      const response = await authFetch(
        `${API_BASE_URL}/api/challenges/assignments/patient/${patientId}`,
      );
      if (!response.ok) {
        setPatientAssignments([]);
        return;
      }
      setPatientAssignments(await response.json());
    } catch (requestError) {
      setChallengeError(requestError.message);
      setPatientAssignments([]);
    }
  }

  async function assignChallenge(patientId, challengeId) {
    setAssigningChallengeId(challengeId);
    setChallengeError("");
    try {
      const response = await authFetch(`${API_BASE_URL}/api/challenges/assignments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patient_id: patientId, challenge_id: challengeId }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail ?? "Impossible d'assigner le défi.");
      }
      await loadPatientAssignments(patientId);
    } catch (requestError) {
      setChallengeError(requestError.message);
    } finally {
      setAssigningChallengeId(null);
    }
  }

  useEffect(() => {
    if (session && dashboard) {
      loadChallengeTemplates();
    }
  }, [session, dashboard]);

  useEffect(() => {
    if (profilePatient?.id) {
      loadPatientAssignments(profilePatient.id);
    } else {
      setPatientAssignments([]);
    }
  }, [profilePatient?.id]);

  if (!session) {
    return <LoginScreen onAuthenticated={(newSession) => setSession(newSession)} />;
  }

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#116a5c" />
        <Text style={styles.loadingText}>Chargement de l'espace médecin</Text>
      </View>
    );
  }

  if (!dashboard) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorTitle}>Interface médecin indisponible</Text>
        <Text style={styles.errorText}>{error || "Le tableau de bord n'a pas pu être chargé."}</Text>
        <Pressable style={styles.refreshButton} onPress={loadDashboard}>
          <Activity size={18} color="#0f766e" />
          <Text style={styles.refreshButtonText}>Réessayer</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.appShell}>
      <View style={[styles.sidebar, isCompact && styles.sidebarCompact]}>
        <View style={styles.brandBlock}>
          <YallaLogo size={46} />
          <View>
            <Text style={styles.brandName}>Yalla</Text>
            <Text style={styles.brandMeta}>Espace médecin</Text>
          </View>
        </View>

        <View style={styles.doctorBlock}>
          <Text style={styles.doctorName}>{displayedDoctor.full_name}</Text>
          <Text style={styles.doctorMeta}>{displayedDoctor.specialty}</Text>
          <Text style={styles.doctorFacility}>{displayedDoctor.facility}</Text>
          {session?.user?.email ? (
            <Text style={styles.sessionEmail}>Connecté : {session.user.email}</Text>
          ) : null}
          <Pressable style={styles.logoutButton} onPress={handleLogout}>
            <LogOut size={14} color="#475569" />
            <Text style={styles.logoutButtonText}>Se déconnecter</Text>
          </Pressable>
        </View>
      </View>

      <ScrollView style={styles.content} contentContainerStyle={styles.contentInner}>
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.pageTitle}>Supervision patients</Text>
            <Text style={styles.pageSubtitle}>Accès, suivi et attribution du rôle patient expert</Text>
          </View>
          <Pressable style={styles.refreshButton} onPress={loadDashboard}>
            <Activity size={18} color="#0f766e" />
            <Text style={styles.refreshButtonText}>Actualiser</Text>
          </Pressable>
        </View>

        {error ? <Text style={styles.errorBanner}>{error}</Text> : null}

        <View style={styles.metricGrid}>
          <Metric icon={Users} label="Patients suivis" value={dashboard.total_patients} />
          <Metric icon={ShieldCheck} label="Accès actifs" value={dashboard.patients_with_access} />
          <Metric icon={UserCheck} label="Patients experts" value={dashboard.expert_patients} />
          <Metric icon={ClipboardList} label="À revoir" value={dashboard.patients_to_review} accent />
        </View>

        <PatientAccountCreator
          creating={creatingPatientAccount}
          error={patientAccountError}
          form={patientAccountForm}
          onChange={setPatientAccountForm}
          onCreate={createPatientAccount}
          result={patientAccountResult}
        />

        <View style={[styles.workspace, isCompact && styles.workspaceCompact]}>
          <View style={styles.patientList}>
            <Text style={styles.sectionTitle}>File active</Text>
            <PatientSearchFilters
              activeFilter={patientFilter}
              onFilterChange={setPatientFilter}
              onSearchChange={setPatientSearch}
              resultCount={filteredPatients.length}
              searchValue={patientSearch}
            />
            {filteredPatients.map((patient) => (
              <PatientRow
                key={patient.id}
                patient={patient}
                selected={patient.id === selectedPatientId}
                onSelect={() => setSelectedPatientId(patient.id)}
                onOpenProfile={() => openPatientProfile(patient.id)}
              />
            ))}
            {filteredPatients.length === 0 ? (
              <Text style={styles.emptySearchText}>Aucun patient ne correspond à cette recherche.</Text>
            ) : null}
          </View>

          <View style={styles.detailPanel}>
            {detailLoading || !selectedPatient ? (
              <View style={styles.detailLoading}>
                <ActivityIndicator color="#116a5c" />
              </View>
            ) : (
              <PatientDetail
                patient={selectedPatient}
                noteDraft={noteDraft}
                savingNote={savingNote}
                onAccessChange={(value) =>
                  patchPatient(selectedPatient.id, "access", { has_app_access: value })
                }
                onExpertChange={(value) =>
                  patchPatient(selectedPatient.id, "expert-role", { is_expert_patient: value })
                }
                onNoteChange={setNoteDraft}
                onOpenProfile={() => openPatientProfile(selectedPatient.id)}
                onSaveNote={() => saveDoctorNote(selectedPatient.id)}
                onDeleteNote={(noteIndex) => deleteDoctorNote(selectedPatient.id, noteIndex)}
              />
            )}
          </View>
        </View>

        <View style={styles.reviewBand}>
          <Text style={styles.sectionTitle}>Priorités médicales</Text>
          <Text style={styles.reviewText}>
            {reviewPatients.length > 0
              ? `${reviewPatients.length} patient à revoir : ${reviewPatients.map((patient) => patient.full_name).join(", ")}.`
              : "Aucun patient marqué à revoir pour le moment."}
          </Text>
        </View>
      </ScrollView>

      <PatientProfileModal
        patient={profilePatient}
        visible={Boolean(profilePatient)}
        onClose={() => setProfilePatient(null)}
        onDeleteNote={(noteIndex) => deleteDoctorNote(profilePatient.id, noteIndex)}
        assignments={patientAssignments}
        challengeTemplates={challengeTemplates}
        onAssignChallenge={(challengeId) => assignChallenge(profilePatient.id, challengeId)}
        assigningChallengeId={assigningChallengeId}
        challengeError={challengeError}
      />
    </View>
  );
}

function PatientSearchFilters({ activeFilter, onFilterChange, onSearchChange, resultCount, searchValue }) {
  const filters = [
    { label: "Tous", value: "all" },
    { label: "Accès app", value: "access" },
    { label: "Patients experts", value: "expert" },
    { label: "À revoir", value: "review" },
  ];

  return (
    <View style={styles.searchPanel}>
      <View style={styles.searchInputWrap}>
        <Search size={17} color="#64748b" />
        <TextInput
          onChangeText={onSearchChange}
          placeholder="Rechercher un patient"
          placeholderTextColor="#94a3b8"
          style={styles.searchInput}
          value={searchValue}
        />
      </View>
      <View style={styles.filterRow}>
        {filters.map((filter) => (
          <Pressable
            key={filter.value}
            onPress={() => onFilterChange(filter.value)}
            style={[styles.filterChip, activeFilter === filter.value && styles.filterChipActive]}
          >
            <Text style={[styles.filterChipText, activeFilter === filter.value && styles.filterChipTextActive]}>
              {filter.label}
            </Text>
          </Pressable>
        ))}
      </View>
      <Text style={styles.searchCount}>{resultCount} résultat{resultCount > 1 ? "s" : ""}</Text>
    </View>
  );
}

function PatientAccountCreator({ creating, error, form, onChange, onCreate, result }) {
  const updateField = (field, value) => onChange((current) => ({ ...current, [field]: value }));

  return (
    <View style={styles.accountPanel}>
      <View style={styles.accountPanelHeader}>
        <View>
          <Text style={styles.sectionTitleCompact}>Créer un compte patient</Text>
          <Text style={styles.accountPanelText}>
            Le patient recevra une invitation Supabase si l'envoi d'emails est activé. Les identifiants temporaires sont affichés ici pour le suivi.
          </Text>
        </View>
        <Pressable style={styles.accountCreateButton} onPress={onCreate} disabled={creating}>
          {creating ? <ActivityIndicator color="#ffffff" /> : <UserCheck size={17} color="#ffffff" />}
          <Text style={styles.accountCreateButtonText}>{creating ? "Création..." : "Créer"}</Text>
        </Pressable>
      </View>

      <View style={styles.accountFormGrid}>
        <View style={styles.accountField}>
          <Text style={styles.accountLabel}>Nom complet</Text>
          <TextInput
            onChangeText={(value) => updateField("fullName", value)}
            placeholder="Karim El Mansouri"
            placeholderTextColor="#94a3b8"
            style={styles.accountInput}
            value={form.fullName}
          />
        </View>
        <View style={styles.accountField}>
          <Text style={styles.accountLabel}>Email patient</Text>
          <TextInput
            autoCapitalize="none"
            keyboardType="email-address"
            onChangeText={(value) => updateField("email", value)}
            placeholder="patient@email.com"
            placeholderTextColor="#94a3b8"
            style={styles.accountInput}
            value={form.email}
          />
        </View>
        <View style={styles.accountFieldSmall}>
          <Text style={styles.accountLabel}>Âge</Text>
          <TextInput
            keyboardType="numeric"
            onChangeText={(value) => updateField("age", value)}
            placeholder="45"
            placeholderTextColor="#94a3b8"
            style={styles.accountInput}
            value={form.age}
          />
        </View>
        <View style={styles.accountFieldWide}>
          <Text style={styles.accountLabel}>Objectif principal</Text>
          <TextInput
            onChangeText={(value) => updateField("primaryGoal", value)}
            placeholder="Stabiliser la glycémie avec une marche quotidienne"
            placeholderTextColor="#94a3b8"
            style={styles.accountInput}
            value={form.primaryGoal}
          />
        </View>
      </View>

      {error ? <Text style={styles.accountError}>{error}</Text> : null}
      {result ? (
        <View style={styles.accountResult}>
          <Text style={styles.accountResultTitle}>Compte créé pour {result.patient.full_name}</Text>
          <Text style={styles.accountResultText}>Login : {result.email}</Text>
          <Text style={styles.accountResultText}>Mot de passe temporaire : {result.temporary_password}</Text>
          <Text style={styles.accountResultText}>{result.email_status}</Text>
        </View>
      ) : null}
    </View>
  );
}

function buildDisplayedDoctor(session, fallbackDoctor) {
  const user = session?.user ?? {};
  const emailName = user.email ? user.email.split("@")[0].replace(/[._-]+/g, " ") : "";
  const formattedEmailName = emailName
    ? `Dr. ${emailName.replace(/\b\w/g, (letter) => letter.toUpperCase())}`
    : null;

  return {
    full_name: user.full_name || formattedEmailName || fallbackDoctor?.full_name || "Médecin connecté",
    specialty: user.specialty || (user.email ? "Spécialité non renseignée" : fallbackDoctor?.specialty) || "Spécialité non renseignée",
    facility: user.facility || (user.email ? "Établissement non renseigné" : fallbackDoctor?.facility) || "Établissement non renseigné",
  };
}

function YallaLogo({ size = 46 }) {
  return <Image source={YALLA_LOGO} style={{ width: size, height: size, borderRadius: size / 2 }} />;
}

function Metric({ icon: Icon, label, value, accent = false }) {
  return (
    <View style={[styles.metricCard, accent && styles.metricCardAccent]}>
      <View style={styles.metricIcon}>
        <Icon size={18} color={accent ? "#b45309" : "#0f766e"} />
      </View>
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

function PatientRow({ patient, selected, onSelect, onOpenProfile }) {
  return (
    <Pressable onPress={onSelect} style={[styles.patientRow, selected && styles.patientRowSelected]}>
      <View style={styles.patientRowTop}>
        <View style={styles.patientIdentity}>
          <Text style={styles.patientName}>{patient.full_name}</Text>
          <Text style={[styles.statusBadge, patient.progress.status === "À revoir" && styles.statusBadgeWarning]}>
            {patient.progress.status}
          </Text>
        </View>
        <Pressable
          accessibilityLabel={`Ouvrir la fiche de ${patient.full_name}`}
          onPress={(event) => {
            event.stopPropagation();
            onOpenProfile();
          }}
          style={styles.iconButton}
        >
          <Eye size={18} color="#0f766e" />
        </Pressable>
      </View>
      <Text style={styles.patientGoal}>{patient.primary_goal}</Text>
      <View style={styles.patientMetaRow}>
        <Text style={styles.patientMeta}>{patient.age} ans</Text>
        <Text style={styles.patientMeta}>{patient.privacy_level}</Text>
      </View>
    </Pressable>
  );
}

function PatientDetail({
  patient,
  noteDraft,
  savingNote,
  onAccessChange,
  onExpertChange,
  onNoteChange,
  onOpenProfile,
  onSaveNote,
  onDeleteNote,
}) {
  const isPrivate = patient.privacy_level === "Données privées";

  return (
    <View>
      <View style={styles.detailHeader}>
        <View style={styles.detailHeaderText}>
          <Text style={styles.detailName}>{patient.full_name}</Text>
          <Text style={styles.detailMeta}>{patient.primary_goal}</Text>
        </View>
        <Pressable accessibilityLabel="Voir le dossier complet" onPress={onOpenProfile} style={styles.iconButtonLarge}>
          <Eye size={22} color="#0f766e" />
        </Pressable>
      </View>

      <View style={styles.controlGrid}>
        <ControlLine
          label="Accès application"
          description="Autorise l'utilisation de Yalla par ce patient"
          value={patient.has_app_access}
          onChange={onAccessChange}
        />
        <ControlLine
          label="Patient expert"
          description="Permet d'accompagner et motiver d'autres patients"
          value={patient.is_expert_patient}
          onChange={onExpertChange}
        />
      </View>

      {isPrivate ? <PrivacyNotice /> : <EvolutionChart points={patient.evolution} />}

      {isPrivate ? null : (
        <View style={styles.progressGrid}>
          <ProgressBlock label="Activité" value={patient.progress.activity_completion_rate} />
          <ProgressBlock label="Défis" value={patient.progress.challenge_completion_rate} />
          <View style={styles.minutesBlock}>
            <Text style={styles.minutesValue}>{patient.progress.weekly_activity_minutes}</Text>
            <Text style={styles.minutesLabel}>min cette semaine</Text>
          </View>
        </View>
      )}

      <Text style={styles.sectionTitle}>Note médecin</Text>
      <View style={styles.noteComposer}>
        <TextInput
          multiline
          numberOfLines={4}
          onChangeText={onNoteChange}
          placeholder="Ajouter une observation, une consigne ou un point à revoir..."
          placeholderTextColor="#94a3b8"
          style={styles.noteInput}
          value={noteDraft}
        />
        <Pressable disabled={savingNote} onPress={onSaveNote} style={styles.saveNoteButton}>
          <Save size={17} color="#ffffff" />
          <Text style={styles.saveNoteButtonText}>{savingNote ? "Enregistrement" : "Enregistrer"}</Text>
        </Pressable>
      </View>

      <Text style={styles.sectionTitle}>Notes enregistrées</Text>
      {patient.doctor_notes.length > 0 ? (
        patient.doctor_notes.map((note, index) => (
          <NoteItem key={`${note}-${index}`} note={note} onDelete={() => onDeleteNote(index)} />
        ))
      ) : (
        <Text style={styles.emptyText}>Aucune note médecin pour ce patient.</Text>
      )}

      <Text style={styles.sectionTitle}>Données visibles</Text>
      <HealthMetrics metrics={patient.health_metrics} />

      {isPrivate ? null : (
        <>
          <Text style={styles.sectionTitle}>Défis actifs</Text>
          {patient.active_challenges.map((challenge) => (
            <Text key={challenge} style={styles.listItem}>
              {challenge}
            </Text>
          ))}
        </>
      )}
    </View>
  );
}

function PatientProfileModal({
  patient,
  visible,
  onClose,
  onDeleteNote,
  assignments = [],
  challengeTemplates = [],
  onAssignChallenge,
  assigningChallengeId,
  challengeError,
}) {
  if (!patient) {
    return null;
  }
  const isPrivate = patient.privacy_level === "Données privées";
  const assignedIds = new Set(assignments.map((a) => a.challenge_id));
  const availableTemplates = challengeTemplates.filter((tpl) => !assignedIds.has(tpl.id));

  return (
    <Modal animationType="fade" transparent visible={visible} onRequestClose={onClose}>
      <View style={styles.modalOverlay}>
        <View style={styles.modalPanel}>
          <View style={styles.modalHeader}>
            <View>
              <Text style={styles.modalTitle}>{patient.full_name}</Text>
              <Text style={styles.modalSubtitle}>
                {patient.age} ans • {patient.privacy_level}
              </Text>
            </View>
            <Pressable accessibilityLabel="Fermer la fiche patient" onPress={onClose} style={styles.iconButtonLarge}>
              <X size={22} color="#475569" />
            </Pressable>
          </View>

          <ScrollView contentContainerStyle={styles.modalContent}>
            <View style={styles.modalSummaryGrid}>
              <ModalStat label="Statut" value={patient.progress.status} />
              <ModalStat label="Dernière consultation" value={formatDate(patient.progress.last_check_in)} />
              {isPrivate ? null : (
                <>
                  <ModalStat label="Activité" value={`${patient.progress.weekly_activity_minutes} min`} />
                  <ModalStat label="Défis" value={`${patient.progress.challenge_completion_rate}%`} />
                </>
              )}
            </View>

            {isPrivate ? <PrivacyNotice /> : <EvolutionChart points={patient.evolution} compact={false} />}

            <Text style={styles.sectionTitle}>Données médicales partagées</Text>
            <HealthMetrics metrics={patient.health_metrics} />

            <Text style={styles.sectionTitle}>Notes médecin</Text>
            {patient.doctor_notes.length > 0 ? (
              patient.doctor_notes.map((note, index) => (
                <NoteItem key={`${note}-${index}`} note={note} onDelete={() => onDeleteNote(index)} />
              ))
            ) : (
              <Text style={styles.emptyText}>Aucune note médecin enregistrée.</Text>
            )}

            <Text style={styles.sectionTitle}>Défis assignés</Text>
            {challengeError ? (
              <Text style={[styles.emptyText, { color: "#b91c1c" }]}>{challengeError}</Text>
            ) : null}
            {assignments.length > 0 ? (
              assignments.map((assignment) => (
                <AssignmentRow key={assignment.id} assignment={assignment} />
              ))
            ) : (
              <Text style={styles.emptyText}>Aucun défi assigné à ce patient.</Text>
            )}

            {availableTemplates.length > 0 ? (
              <>
                <Text style={styles.sectionTitle}>Assigner un nouveau défi</Text>
                {availableTemplates.map((template) => (
                  <Pressable
                    key={template.id}
                    style={styles.assignButton}
                    onPress={() => onAssignChallenge?.(template.id)}
                    disabled={assigningChallengeId === template.id}
                  >
                    <Target size={16} color="#0f766e" />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.assignButtonTitle}>{template.title}</Text>
                      <Text style={styles.assignButtonMeta}>
                        {template.category} • {template.target_value} {template.target_unit} • {template.duration_days}j • {template.difficulty}
                      </Text>
                    </View>
                    {assigningChallengeId === template.id ? (
                      <ActivityIndicator color="#0f766e" />
                    ) : (
                      <Plus size={16} color="#0f766e" />
                    )}
                  </Pressable>
                ))}
              </>
            ) : null}

            <Text style={styles.sectionTitle}>Notes de suivi</Text>
            {patient.care_notes.map((note) => (
              <Text key={note} style={styles.listItem}>
                {note}
              </Text>
            ))}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

function PrivacyNotice() {
  return (
    <View style={styles.privacyNotice}>
      <ShieldCheck size={20} color="#0f766e" />
      <View style={styles.privacyNoticeText}>
        <Text style={styles.privacyNoticeTitle}>Données privées activées</Text>
        <Text style={styles.privacyNoticeBody}>
          Le suivi des défis, les minutes d'activité de la semaine et l'évolution détaillée ne sont pas visibles.
          Seules les données de la dernière consultation sont affichées.
        </Text>
      </View>
    </View>
  );
}

function NoteItem({ note, onDelete }) {
  return (
    <View style={styles.noteItemRow}>
      <Text style={styles.noteItemText}>{note}</Text>
      <Pressable accessibilityLabel="Effacer la note" onPress={onDelete} style={styles.deleteNoteButton}>
        <Trash2 size={16} color="#991b1b" />
      </Pressable>
    </View>
  );
}

function AssignmentRow({ assignment }) {
  const challenge = assignment.challenge;
  const statusColor =
    assignment.status === "completed"
      ? "#047857"
      : assignment.status === "abandoned"
        ? "#b91c1c"
        : "#0f766e";
  return (
    <View style={styles.assignmentRow}>
      <View style={styles.assignmentHeader}>
        <Text style={styles.assignmentTitle}>{challenge.title}</Text>
        <Text style={[styles.assignmentStatus, { color: statusColor }]}>
          {assignment.status}
        </Text>
      </View>
      <Text style={styles.assignmentMeta}>
        {challenge.category} • {assignment.current_value}/{challenge.target_value} {challenge.target_unit}
        {" "}• échéance {formatDate(assignment.due_on)}
      </Text>
      <View style={styles.assignmentBar}>
        <View style={[styles.assignmentBarFill, { width: `${assignment.progress}%` }]} />
      </View>
      <Text style={styles.assignmentProgressText}>{assignment.progress}%</Text>
    </View>
  );
}

function ModalStat({ label, value }) {
  return (
    <View style={styles.modalStat}>
      <Text style={styles.modalStatValue}>{value}</Text>
      <Text style={styles.modalStatLabel}>{label}</Text>
    </View>
  );
}

function HealthMetrics({ metrics }) {
  return (
    <View style={styles.metricsList}>
      {metrics.map((metric) => (
        <View key={metric.label} style={styles.healthMetric}>
          <Text style={styles.healthMetricLabel}>{metric.label}</Text>
          <Text style={styles.healthMetricValue}>{metric.value}</Text>
          <Text style={styles.healthMetricTrend}>{metric.trend}</Text>
        </View>
      ))}
    </View>
  );
}

function EvolutionChart({ points, compact = true }) {
  const hba1cValues = points.map((point) => point.hba1c);
  const activityValues = points.map((point) => point.weekly_activity_minutes);
  const challengeValues = points.map((point) => point.challenge_completion_rate);
  const minHba1c = Math.min(...hba1cValues) - 0.2;
  const maxHba1c = Math.max(...hba1cValues) + 0.2;
  const chartWidth = 640;
  const chartHeight = compact ? 220 : 270;
  const padding = 34;
  const plotWidth = chartWidth - padding * 2;
  const plotHeight = chartHeight - padding * 2;
  const hba1cLine = buildLinePoints(points, hba1cValues, minHba1c, maxHba1c, chartWidth, chartHeight, padding);
  const activityLine = buildLinePoints(
    points,
    activityValues,
    0,
    Math.max(...activityValues, 240),
    chartWidth,
    chartHeight,
    padding,
  );
  const challengeLine = buildLinePoints(points, challengeValues, 0, 100, chartWidth, chartHeight, padding);

  return (
    <View style={styles.chartPanel}>
      <View style={styles.chartHeader}>
        <View>
          <Text style={styles.sectionTitle}>Évolution dans le temps</Text>
          <Text style={styles.chartSubtitle}>HbA1c, activité hebdomadaire et régularité des défis</Text>
        </View>
        <TrendingDown size={20} color="#0f766e" />
      </View>

      <View style={styles.lineChartFrame}>
        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} style={styles.lineChart}>
          <line x1={padding} y1={padding} x2={padding} y2={chartHeight - padding} stroke="#cbd5e1" strokeWidth="1" />
          <line
            x1={padding}
            y1={chartHeight - padding}
            x2={chartWidth - padding}
            y2={chartHeight - padding}
            stroke="#cbd5e1"
            strokeWidth="1"
          />
          {[0.25, 0.5, 0.75].map((ratio) => (
            <line
              key={ratio}
              x1={padding}
              y1={padding + plotHeight * ratio}
              x2={chartWidth - padding}
              y2={padding + plotHeight * ratio}
              stroke="#e2e8f0"
              strokeDasharray="6 6"
              strokeWidth="1"
            />
          ))}
          <polyline fill="none" points={hba1cLine.path} stroke="#0f766e" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
          <polyline fill="none" points={activityLine.path} stroke="#2563eb" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" />
          <polyline fill="none" points={challengeLine.path} stroke="#d97706" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" />
          {hba1cLine.points.map((point, index) => (
            <g key={`hba1c-${point.label}`}>
              <circle cx={point.x} cy={point.y} fill="#ffffff" r="6" stroke="#0f766e" strokeWidth="3" />
              <text fill="#13201f" fontSize="13" fontWeight="700" textAnchor="middle" x={point.x} y={point.y - 12}>
                {hba1cValues[index].toFixed(1)}%
              </text>
            </g>
          ))}
          {activityLine.points.map((point) => (
            <circle key={`activity-${point.label}`} cx={point.x} cy={point.y} fill="#2563eb" r="4" />
          ))}
          {challengeLine.points.map((point) => (
            <circle key={`challenge-${point.label}`} cx={point.x} cy={point.y} fill="#d97706" r="4" />
          ))}
          {points.map((point, index) => {
            const x = padding + (plotWidth / Math.max(points.length - 1, 1)) * index;
            return (
              <text key={point.recorded_on} fill="#64748b" fontSize="13" fontWeight="700" textAnchor="middle" x={x} y={chartHeight - 8}>
                {formatMonth(point.recorded_on)}
              </text>
            );
          })}
        </svg>
      </View>

      <View style={styles.chartLegend}>
        <Legend color="#0f766e" label="HbA1c" />
        <Legend color="#2563eb" label="Minutes activité" />
        <Legend color="#d97706" label="Défis complétés" />
      </View>
    </View>
  );
}

function buildLinePoints(points, values, minValue, maxValue, width, height, padding) {
  const range = Math.max(maxValue - minValue, 1);
  const plotWidth = width - padding * 2;
  const plotHeight = height - padding * 2;
  const coordinates = points.map((point, index) => {
    const x = padding + (plotWidth / Math.max(points.length - 1, 1)) * index;
    const y = height - padding - ((values[index] - minValue) / range) * plotHeight;

    return {
      label: point.recorded_on,
      x,
      y: Math.min(height - padding, Math.max(padding, y)),
    };
  });

  return {
    path: coordinates.map((point) => `${point.x},${point.y}`).join(" "),
    points: coordinates,
  };
}

function Legend({ color, label }) {
  return (
    <View style={styles.legendItem}>
      <View style={[styles.legendSwatch, { backgroundColor: color }]} />
      <Text style={styles.legendText}>{label}</Text>
    </View>
  );
}

function ControlLine({ label, description, value, onChange }) {
  return (
    <View style={styles.controlLine}>
      <View style={styles.controlText}>
        <Text style={styles.controlLabel}>{label}</Text>
        <Text style={styles.controlDescription}>{description}</Text>
      </View>
      <Switch value={value} onValueChange={onChange} activeThumbColor="#0f766e" />
    </View>
  );
}

function ProgressBlock({ label, value }) {
  return (
    <View style={styles.progressBlock}>
      <Text style={styles.progressValue}>{value}%</Text>
      <Text style={styles.progressLabel}>{label}</Text>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: `${value}%` }]} />
      </View>
    </View>
  );
}

function formatMonth(value) {
  return new Intl.DateTimeFormat("fr-FR", { month: "short" }).format(new Date(value));
}

function formatDate(value) {
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value));
}

const styles = StyleSheet.create({
  appShell: {
    minHeight: "100vh",
    flexDirection: "row",
    backgroundColor: "#f5f7f8",
  },
  sidebar: {
    width: 280,
    backgroundColor: "#102a2a",
    padding: 24,
    gap: 28,
  },
  sidebarCompact: {
    display: "none",
  },
  brandBlock: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  brandName: {
    color: "#f8fafc",
    fontSize: 22,
    fontWeight: "800",
  },
  brandMeta: {
    color: "#a7c7c2",
    fontSize: 13,
  },
  doctorBlock: {
    borderTopWidth: 1,
    borderTopColor: "#294747",
    paddingTop: 20,
  },
  doctorName: {
    color: "#f8fafc",
    fontSize: 18,
    fontWeight: "700",
  },
  doctorMeta: {
    color: "#c6d7d4",
    marginTop: 8,
    fontSize: 14,
    lineHeight: 20,
  },
  doctorFacility: {
    color: "#8fb4ae",
    marginTop: 6,
    fontSize: 13,
  },
  content: {
    flex: 1,
  },
  contentInner: {
    padding: 28,
    gap: 22,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 16,
    flexWrap: "wrap",
  },
  pageTitle: {
    color: "#13201f",
    fontSize: 30,
    fontWeight: "800",
  },
  pageSubtitle: {
    color: "#64748b",
    marginTop: 6,
    fontSize: 15,
  },
  refreshButton: {
    minHeight: 42,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#b7d4cf",
    backgroundColor: "#ffffff",
    paddingHorizontal: 16,
  },
  refreshButtonText: {
    color: "#0f766e",
    fontWeight: "700",
  },
  errorBanner: {
    color: "#991b1b",
    backgroundColor: "#fee2e2",
    borderRadius: 8,
    padding: 12,
    fontWeight: "600",
  },
  metricGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 14,
  },
  metricCard: {
    minWidth: 180,
    flex: 1,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#d9e2e1",
    backgroundColor: "#ffffff",
    padding: 18,
  },
  metricCardAccent: {
    borderColor: "#f2d7a6",
    backgroundColor: "#fffbeb",
  },
  metricIcon: {
    width: 34,
    height: 34,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#eef7f5",
  },
  metricValue: {
    color: "#13201f",
    marginTop: 12,
    fontSize: 28,
    fontWeight: "800",
  },
  metricLabel: {
    color: "#64748b",
    marginTop: 4,
    fontSize: 14,
  },
  workspace: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 20,
  },
  workspaceCompact: {
    flexDirection: "column",
  },
  patientList: {
    width: 390,
    maxWidth: "100%",
    gap: 10,
  },
  searchPanel: {
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#d9e2e1",
    backgroundColor: "#ffffff",
    padding: 12,
    gap: 10,
  },
  searchInputWrap: {
    minHeight: 42,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#cbd5e1",
    backgroundColor: "#f8fafc",
    paddingHorizontal: 12,
  },
  searchInput: {
    flex: 1,
    color: "#13201f",
    fontSize: 14,
    outlineStyle: "none",
  },
  filterRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  filterChip: {
    minHeight: 32,
    justifyContent: "center",
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#d9e2e1",
    backgroundColor: "#ffffff",
    paddingHorizontal: 11,
  },
  filterChipActive: {
    borderColor: "#0f766e",
    backgroundColor: "#ccfbf1",
  },
  filterChipText: {
    color: "#475569",
    fontSize: 12,
    fontWeight: "800",
  },
  filterChipTextActive: {
    color: "#0f766e",
  },
  searchCount: {
    color: "#64748b",
    fontSize: 12,
    fontWeight: "700",
  },
  accountPanel: {
    borderWidth: 1,
    borderColor: "#d9e2e1",
    backgroundColor: "#ffffff",
    borderRadius: 8,
    padding: 16,
    gap: 14,
  },
  accountPanelHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 14,
  },
  sectionTitleCompact: {
    color: "#13201f",
    fontSize: 16,
    fontWeight: "800",
  },
  accountPanelText: {
    color: "#64748b",
    marginTop: 5,
    fontSize: 13,
    lineHeight: 18,
  },
  accountCreateButton: {
    minHeight: 40,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderRadius: 8,
    backgroundColor: "#0f766e",
    paddingHorizontal: 14,
  },
  accountCreateButtonText: {
    color: "#ffffff",
    fontWeight: "800",
  },
  accountFormGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
  },
  accountField: {
    flex: 1,
    minWidth: 220,
  },
  accountFieldSmall: {
    width: 96,
  },
  accountFieldWide: {
    flex: 2,
    minWidth: 260,
  },
  accountLabel: {
    color: "#334155",
    marginBottom: 6,
    fontSize: 12,
    fontWeight: "800",
  },
  accountInput: {
    minHeight: 42,
    borderWidth: 1,
    borderColor: "#cbd5e1",
    borderRadius: 8,
    color: "#13201f",
    backgroundColor: "#ffffff",
    paddingHorizontal: 12,
    fontSize: 14,
    outlineStyle: "none",
  },
  accountError: {
    color: "#b91c1c",
    fontWeight: "700",
  },
  accountResult: {
    borderWidth: 1,
    borderColor: "#bbf7d0",
    borderRadius: 8,
    backgroundColor: "#ecfdf5",
    padding: 12,
    gap: 4,
  },
  accountResultTitle: {
    color: "#065f46",
    fontWeight: "800",
  },
  accountResultText: {
    color: "#047857",
    fontSize: 13,
    lineHeight: 18,
  },
  emptySearchText: {
    color: "#64748b",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#d9e2e1",
    backgroundColor: "#ffffff",
    padding: 14,
    fontSize: 14,
    lineHeight: 20,
  },
  sectionTitle: {
    color: "#13201f",
    marginBottom: 10,
    marginTop: 18,
    fontSize: 16,
    fontWeight: "800",
  },
  patientRow: {
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#d9e2e1",
    backgroundColor: "#ffffff",
    padding: 14,
  },
  patientRowSelected: {
    borderColor: "#0f766e",
    backgroundColor: "#f0fdfa",
  },
  patientRowTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 10,
  },
  patientIdentity: {
    flex: 1,
    gap: 8,
  },
  patientName: {
    color: "#13201f",
    flex: 1,
    fontSize: 16,
    fontWeight: "800",
  },
  statusBadge: {
    alignSelf: "flex-start",
    color: "#0f766e",
    backgroundColor: "#ccfbf1",
    borderRadius: 999,
    paddingHorizontal: 9,
    paddingVertical: 3,
    fontSize: 12,
    fontWeight: "800",
  },
  statusBadgeWarning: {
    color: "#92400e",
    backgroundColor: "#fde68a",
  },
  patientGoal: {
    color: "#475569",
    marginTop: 8,
    fontSize: 14,
    lineHeight: 20,
  },
  patientMetaRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 10,
  },
  patientMeta: {
    color: "#64748b",
    fontSize: 12,
  },
  iconButton: {
    width: 38,
    height: 38,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#eef7f5",
    borderWidth: 1,
    borderColor: "#c9e7e1",
  },
  iconButtonLarge: {
    width: 44,
    height: 44,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#d9e2e1",
  },
  detailPanel: {
    flex: 1,
    minWidth: 320,
    borderLeftWidth: 1,
    borderLeftColor: "#d9e2e1",
    paddingLeft: 20,
  },
  detailLoading: {
    minHeight: 320,
    alignItems: "center",
    justifyContent: "center",
  },
  detailHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#d9e2e1",
    paddingBottom: 16,
  },
  detailHeaderText: {
    flex: 1,
  },
  detailName: {
    color: "#13201f",
    fontSize: 24,
    fontWeight: "800",
  },
  detailMeta: {
    color: "#64748b",
    marginTop: 6,
    fontSize: 14,
    lineHeight: 20,
  },
  controlGrid: {
    gap: 10,
    marginTop: 18,
  },
  controlLine: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 16,
    borderRadius: 8,
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#d9e2e1",
    padding: 14,
  },
  controlText: {
    flex: 1,
  },
  controlLabel: {
    color: "#13201f",
    fontSize: 15,
    fontWeight: "800",
  },
  controlDescription: {
    color: "#64748b",
    marginTop: 4,
    fontSize: 13,
    lineHeight: 18,
  },
  chartPanel: {
    borderRadius: 8,
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#d9e2e1",
    marginTop: 18,
    padding: 16,
  },
  chartHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 14,
  },
  chartSubtitle: {
    color: "#64748b",
    fontSize: 13,
    lineHeight: 18,
  },
  lineChartFrame: {
    width: "100%",
    minHeight: 230,
    borderRadius: 8,
    backgroundColor: "#f8fafc",
    borderWidth: 1,
    borderColor: "#e2e8f0",
    marginTop: 16,
    overflow: "hidden",
  },
  lineChart: {
    width: "100%",
    height: "100%",
    minHeight: 230,
    display: "block",
  },
  chartArea: {
    height: 190,
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#cbd5e1",
    marginTop: 16,
    paddingTop: 12,
  },
  chartAreaLarge: {
    height: 240,
  },
  chartColumn: {
    flex: 1,
    alignItems: "center",
    minWidth: 54,
  },
  chartBars: {
    height: "100%",
    width: "100%",
    flexDirection: "row",
    alignItems: "flex-end",
    justifyContent: "center",
    gap: 5,
  },
  hba1cBar: {
    width: 10,
    borderRadius: 999,
    backgroundColor: "#0f766e",
  },
  activityBar: {
    width: 10,
    borderRadius: 999,
    backgroundColor: "#2563eb",
  },
  challengeBar: {
    width: 10,
    borderRadius: 999,
    backgroundColor: "#d97706",
  },
  chartValue: {
    color: "#13201f",
    marginTop: 8,
    fontSize: 12,
    fontWeight: "800",
  },
  chartLabel: {
    color: "#64748b",
    marginTop: 2,
    fontSize: 12,
  },
  chartLegend: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
    marginTop: 14,
  },
  legendItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  legendSwatch: {
    width: 10,
    height: 10,
    borderRadius: 999,
  },
  legendText: {
    color: "#64748b",
    fontSize: 12,
    fontWeight: "700",
  },
  progressGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
    marginTop: 18,
  },
  progressBlock: {
    flex: 1,
    minWidth: 150,
    borderRadius: 8,
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#d9e2e1",
    padding: 14,
  },
  progressValue: {
    color: "#13201f",
    fontSize: 24,
    fontWeight: "800",
  },
  progressLabel: {
    color: "#64748b",
    marginTop: 4,
    fontSize: 13,
  },
  progressTrack: {
    height: 8,
    borderRadius: 999,
    backgroundColor: "#e2e8f0",
    marginTop: 12,
    overflow: "hidden",
  },
  progressFill: {
    height: 8,
    borderRadius: 999,
    backgroundColor: "#0f766e",
  },
  minutesBlock: {
    flex: 1,
    minWidth: 150,
    borderRadius: 8,
    backgroundColor: "#102a2a",
    padding: 14,
  },
  minutesValue: {
    color: "#ffffff",
    fontSize: 24,
    fontWeight: "800",
  },
  minutesLabel: {
    color: "#b8d2ce",
    marginTop: 4,
    fontSize: 13,
  },
  noteComposer: {
    borderRadius: 8,
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#d9e2e1",
    padding: 12,
    gap: 10,
  },
  noteInput: {
    minHeight: 96,
    color: "#13201f",
    fontSize: 14,
    lineHeight: 20,
    outlineStyle: "none",
    textAlignVertical: "top",
  },
  saveNoteButton: {
    alignSelf: "flex-end",
    minHeight: 40,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderRadius: 8,
    backgroundColor: "#0f766e",
    paddingHorizontal: 14,
  },
  saveNoteButtonText: {
    color: "#ffffff",
    fontWeight: "800",
  },
  noteItemRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    color: "#334155",
    borderLeftWidth: 3,
    borderLeftColor: "#2563eb",
    backgroundColor: "#eff6ff",
    borderRadius: 8,
    marginBottom: 8,
    padding: 10,
  },
  noteItemText: {
    flex: 1,
    color: "#334155",
    lineHeight: 20,
  },
  deleteNoteButton: {
    width: 34,
    height: 34,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#fee2e2",
    borderWidth: 1,
    borderColor: "#fecaca",
  },
  privacyNotice: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#b7d4cf",
    backgroundColor: "#f0fdfa",
    marginTop: 18,
    padding: 14,
  },
  privacyNoticeText: {
    flex: 1,
  },
  privacyNoticeTitle: {
    color: "#134e4a",
    fontSize: 15,
    fontWeight: "800",
  },
  privacyNoticeBody: {
    color: "#475569",
    marginTop: 4,
    fontSize: 13,
    lineHeight: 19,
  },
  emptyText: {
    color: "#64748b",
    fontSize: 14,
    lineHeight: 20,
  },
  metricsList: {
    gap: 10,
  },
  healthMetric: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#e2e8f0",
    paddingVertical: 10,
  },
  healthMetricLabel: {
    color: "#475569",
    flex: 1,
    fontWeight: "700",
  },
  healthMetricValue: {
    color: "#13201f",
    minWidth: 76,
    textAlign: "right",
    fontWeight: "800",
  },
  healthMetricTrend: {
    color: "#64748b",
    minWidth: 140,
    textAlign: "right",
    fontSize: 13,
  },
  listItem: {
    color: "#334155",
    borderLeftWidth: 3,
    borderLeftColor: "#0f766e",
    paddingLeft: 10,
    paddingVertical: 6,
    lineHeight: 20,
  },
  reviewBand: {
    borderTopWidth: 1,
    borderTopColor: "#d9e2e1",
    paddingTop: 6,
  },
  reviewText: {
    color: "#475569",
    fontSize: 14,
    lineHeight: 20,
  },
  modalOverlay: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(15, 23, 42, 0.42)",
    padding: 24,
  },
  modalPanel: {
    width: "min(980px, 100%)",
    maxHeight: "92vh",
    borderRadius: 8,
    backgroundColor: "#ffffff",
    overflow: "hidden",
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#d9e2e1",
    padding: 20,
  },
  modalTitle: {
    color: "#13201f",
    fontSize: 24,
    fontWeight: "800",
  },
  modalSubtitle: {
    color: "#64748b",
    marginTop: 4,
    fontSize: 14,
  },
  modalContent: {
    padding: 20,
  },
  modalSummaryGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
  },
  modalStat: {
    flex: 1,
    minWidth: 160,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#d9e2e1",
    backgroundColor: "#f8fafc",
    padding: 14,
  },
  modalStatValue: {
    color: "#13201f",
    fontSize: 18,
    fontWeight: "800",
  },
  modalStatLabel: {
    color: "#64748b",
    marginTop: 4,
    fontSize: 13,
  },
  centered: {
    minHeight: "100vh",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#f5f7f8",
  },
  loadingText: {
    color: "#475569",
    marginTop: 12,
    fontWeight: "700",
  },
  errorTitle: {
    color: "#13201f",
    fontSize: 22,
    fontWeight: "800",
  },
  errorText: {
    color: "#64748b",
    marginBottom: 18,
    marginTop: 8,
    maxWidth: 420,
    textAlign: "center",
  },
  sessionEmail: {
    marginTop: 12,
    fontSize: 12,
    color: "#94a3b8",
  },
  logoutButton: {
    marginTop: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    alignSelf: "flex-start",
    backgroundColor: "#e2e8f0",
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
  },
  logoutButtonText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#475569",
  },
  assignmentRow: {
    backgroundColor: "#f8fafc",
    borderRadius: 12,
    padding: 14,
    marginTop: 10,
    gap: 6,
  },
  assignmentHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  assignmentTitle: {
    fontWeight: "700",
    color: "#0f172a",
    fontSize: 14,
    flex: 1,
  },
  assignmentStatus: {
    fontSize: 12,
    fontWeight: "700",
    textTransform: "uppercase",
  },
  assignmentMeta: {
    fontSize: 12,
    color: "#64748b",
  },
  assignmentBar: {
    height: 6,
    borderRadius: 999,
    backgroundColor: "#e2e8f0",
    overflow: "hidden",
    marginTop: 4,
  },
  assignmentBarFill: {
    height: "100%",
    backgroundColor: "#0f766e",
  },
  assignmentProgressText: {
    fontSize: 11,
    color: "#475569",
    fontWeight: "600",
    alignSelf: "flex-end",
  },
  assignButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: "#ecfdf5",
    borderColor: "#bbf7d0",
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    marginTop: 8,
  },
  assignButtonTitle: {
    fontWeight: "700",
    color: "#065f46",
    fontSize: 14,
  },
  assignButtonMeta: {
    fontSize: 12,
    color: "#047857",
    marginTop: 2,
  },
});
