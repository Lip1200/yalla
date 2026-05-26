/**
 * Pedometer + GPS demo card for the patient-app.
 *
 * Demonstrates the Phase 1 health-data flow from issue #43:
 *   1. Request OS permission for motion / steps.
 *   2. Read today's cumulative steps + watch live updates.
 *   3. Push the step count to the most recent active steps-based
 *      challenge assignment via POST /api/challenges/assignments/{id}/log.
 *   4. Show the awarded badges that come back in the response.
 *
 * Designed to be plugged into ProgressScreen with a single line:
 *     <PedometerCard patientId={activePatientId} />
 *
 * No HealthKit / Health Connect — that's Phase 2 (issue #23 + #34).
 */
import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { Activity, MapPin, RefreshCw, Trophy } from "lucide-react-native";

import { apiGet, apiPost } from "../services/api";
import {
  getCurrentCoords,
  requestLocationPermission,
} from "../services/location";
import {
  getPedometerPermission,
  getStepsToday,
  isPedometerAvailable,
  requestPedometerPermission,
  subscribeSteps,
} from "../services/pedometer";

export default function PedometerCard({ patientId }) {
  const [available, setAvailable] = useState(null); // null = checking
  const [granted, setGranted] = useState(false);
  const [stepsToday, setStepsToday] = useState(0);
  const [liveSteps, setLiveSteps] = useState(0);
  const [coords, setCoords] = useState(null);
  const [syncStatus, setSyncStatus] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");
  const [newlyAwarded, setNewlyAwarded] = useState([]);

  // Initial check: is pedometer available + already permitted?
  useEffect(() => {
    (async () => {
      const ok = await isPedometerAvailable();
      setAvailable(ok);
      if (!ok) return;
      const has = await getPedometerPermission();
      setGranted(has);
      if (has) {
        setStepsToday(await getStepsToday());
      }
    })();
  }, []);

  // Live subscription once permission granted.
  useEffect(() => {
    if (!granted) return undefined;
    const sub = subscribeSteps((delta) => setLiveSteps((prev) => prev + delta));
    return () => sub.remove();
  }, [granted]);

  async function handleEnable() {
    setError("");
    const ok = await requestPedometerPermission();
    setGranted(ok);
    if (!ok) {
      setError("Permission refusée — active le suivi des pas dans les réglages du téléphone.");
      return;
    }
    setStepsToday(await getStepsToday());
  }

  async function handleLocate() {
    setError("");
    const granted = await requestLocationPermission();
    if (!granted) {
      setError("Permission de localisation refusée.");
      return;
    }
    setCoords(await getCurrentCoords());
  }

  async function handleSync() {
    setError("");
    setSyncStatus("");
    setNewlyAwarded([]);
    setSyncing(true);
    try {
      // Trouver le dernier défi steps actif du patient.
      const assignments = await apiGet(
        `/api/challenges/assignments/patient/${patientId}?status_filter=active`,
      );
      const stepsAssignment = (assignments ?? []).find(
        (a) => a?.challenge?.target_unit === "steps",
      );
      if (!stepsAssignment) {
        setSyncStatus(
          "Aucun défi de pas actif. Demande à ton médecin de t'en assigner un, puis réessaie.",
        );
        return;
      }

      // Le delta à pousser = pas depuis le dernier sync. Ici on envoie tout
      // ce qu'on a aujourd'hui en local (simplification — un vrai sync
      // diff-erait avec ce qui est déjà comptabilisé côté backend).
      const value = stepsToday + liveSteps;
      if (value <= 0) {
        setSyncStatus("Aucun pas à synchroniser pour l'instant.");
        return;
      }

      const result = await apiPost(
        `/api/challenges/assignments/${stepsAssignment.id}/log`,
        { value, source: "pedometer" },
      );
      const progress = result?.assignment?.progress ?? 0;
      const badges = result?.newly_awarded_badges ?? [];
      setNewlyAwarded(badges);
      setSyncStatus(
        `Synchronisé ! Progression : ${progress}% sur "${stepsAssignment.challenge.title}".`,
      );
    } catch (e) {
      setError(e?.message ?? "Synchronisation impossible.");
    } finally {
      setSyncing(false);
    }
  }

  if (available === null) {
    return (
      <View style={styles.card}>
        <ActivityIndicator color="#0f766e" />
      </View>
    );
  }

  if (!available) {
    return (
      <View style={styles.card}>
        <Text style={styles.title}>Podomètre indisponible</Text>
        <Text style={styles.body}>
          Ton appareil ne supporte pas le suivi des pas via Expo Go. Cette
          fonctionnalité sera disponible avec un Dev Build (cf. issue #34).
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Activity size={20} color="#0f766e" />
        <Text style={styles.title}>Mon activité</Text>
      </View>

      {!granted ? (
        <>
          <Text style={styles.body}>
            Active le suivi des pas pour faire avancer automatiquement tes défis d'activité.
          </Text>
          <Pressable style={styles.primaryBtn} onPress={handleEnable}>
            <Text style={styles.primaryBtnText}>Activer le suivi des pas</Text>
          </Pressable>
        </>
      ) : (
        <>
          <View style={styles.statsRow}>
            <View style={styles.stat}>
              <Text style={styles.statValue}>{stepsToday + liveSteps}</Text>
              <Text style={styles.statLabel}>pas aujourd'hui</Text>
            </View>
            <Pressable
              style={[styles.secondaryBtn, syncing && styles.btnDisabled]}
              onPress={handleSync}
              disabled={syncing}
            >
              {syncing ? (
                <ActivityIndicator color="#ffffff" />
              ) : (
                <>
                  <RefreshCw size={14} color="#ffffff" />
                  <Text style={styles.secondaryBtnText}>Synchroniser avec Yalla</Text>
                </>
              )}
            </Pressable>
          </View>

          {coords ? (
            <Text style={styles.gpsLine}>
              📍 {coords.latitude.toFixed(4)}, {coords.longitude.toFixed(4)}
              {coords.fromFallback ? " (position approchée — Genève centre)" : ""}
            </Text>
          ) : (
            <Pressable style={styles.linkBtn} onPress={handleLocate}>
              <MapPin size={14} color="#0f766e" />
              <Text style={styles.linkText}>Localiser pour les restos proches</Text>
            </Pressable>
          )}

          {syncStatus ? <Text style={styles.status}>{syncStatus}</Text> : null}

          {newlyAwarded.length > 0 ? (
            <View style={styles.badgesBlock}>
              <Trophy size={18} color="#b45309" />
              <Text style={styles.badgesTitle}>Nouveau(x) badge(s) débloqué(s) !</Text>
              {newlyAwarded.map((b) => (
                <Text key={b.code} style={styles.badgeLine}>
                  {b.icon} {b.name}
                </Text>
              ))}
            </View>
          ) : null}
        </>
      )}

      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    shadowColor: "#0f172a",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 2,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
  },
  title: {
    fontSize: 16,
    fontWeight: "700",
    color: "#0f172a",
  },
  body: {
    color: "#475569",
    fontSize: 14,
    marginBottom: 12,
  },
  primaryBtn: {
    backgroundColor: "#0f766e",
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
  },
  primaryBtnText: {
    color: "#ffffff",
    fontWeight: "600",
  },
  statsRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    marginBottom: 12,
  },
  stat: {
    flex: 1,
  },
  statValue: {
    fontSize: 28,
    fontWeight: "800",
    color: "#0f172a",
  },
  statLabel: {
    color: "#64748b",
    fontSize: 12,
  },
  secondaryBtn: {
    flexDirection: "row",
    gap: 6,
    alignItems: "center",
    backgroundColor: "#0f766e",
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 10,
  },
  secondaryBtnText: {
    color: "#ffffff",
    fontWeight: "600",
    fontSize: 13,
  },
  btnDisabled: {
    opacity: 0.6,
  },
  linkBtn: {
    flexDirection: "row",
    gap: 6,
    alignItems: "center",
    marginTop: 4,
  },
  linkText: {
    color: "#0f766e",
    fontWeight: "600",
    fontSize: 13,
  },
  gpsLine: {
    color: "#475569",
    fontSize: 12,
    marginTop: 4,
  },
  status: {
    marginTop: 10,
    color: "#0f766e",
    fontSize: 13,
  },
  error: {
    marginTop: 10,
    color: "#b91c1c",
    fontSize: 13,
  },
  badgesBlock: {
    marginTop: 12,
    backgroundColor: "#fef3c7",
    padding: 12,
    borderRadius: 10,
  },
  badgesTitle: {
    fontWeight: "700",
    color: "#92400e",
    marginTop: 4,
  },
  badgeLine: {
    color: "#92400e",
    marginTop: 4,
  },
});
