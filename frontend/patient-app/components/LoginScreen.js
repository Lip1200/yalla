/**
 * LoginScreen — patient-app authentication entry point.
 *
 * Login-only. Patients no longer self-signup from this screen — they
 * arrive via an invitation link sent by their doctor (cf. #33 /
 * SetupAccountScreen). This matches the clinical onboarding model
 * agreed for the demo: doctors enrol their patients from doctor-web,
 * which provisions a profile row and emails an invitation_url with a
 * one-shot token; the patient finishes the setup with a chosen password
 * through SetupAccountScreen and lands authenticated. Self-signup paths
 * are intentionally removed so the access flow goes through the doctor.
 */
import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { LogIn, ShieldCheck } from "lucide-react-native";

import { loginPatient } from "../services/auth";

export default function LoginScreen({ onAuthenticated }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit() {
    setError("");

    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password) {
      setError("Email et mot de passe sont requis.");
      return;
    }

    setSubmitting(true);
    try {
      const session = await loginPatient(trimmedEmail, password);
      onAuthenticated?.(session);
    } catch (e) {
      const status = e?.status;
      if (status === 401) {
        setError("Identifiants invalides. Vérifie l'email et le mot de passe.");
      } else {
        setError(e?.message ?? "Erreur inattendue.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.shell}>
      <View style={styles.card}>
        <View style={styles.headerRow}>
          <ShieldCheck size={28} color="#0f766e" />
          <Text style={styles.title}>Connexion</Text>
        </View>
        <Text style={styles.body}>
          Connecte-toi avec l'email et le mot de passe que tu as définis depuis le lien envoyé par ton médecin.
        </Text>

        {error ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}

        <Text style={styles.label}>Email</Text>
        <TextInput
          style={styles.input}
          value={email}
          onChangeText={setEmail}
          placeholder="email@example.com"
          autoCapitalize="none"
          keyboardType="email-address"
          editable={!submitting}
        />

        <Text style={styles.label}>Mot de passe</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          placeholder="Ton mot de passe"
          secureTextEntry
          editable={!submitting}
        />

        <Pressable
          style={[styles.primaryBtn, submitting && styles.btnDisabled]}
          onPress={handleSubmit}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <View style={styles.btnInner}>
              <LogIn size={18} color="#ffffff" />
              <Text style={styles.primaryBtnText}>Se connecter</Text>
            </View>
          )}
        </Pressable>

        <Text style={styles.helperText}>
          Tu n'as pas encore d'accès ? Demande à ton médecin de t'envoyer une invitation.
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  shell: {
    flexGrow: 1,
    backgroundColor: "#f5f7f8",
    padding: 20,
    justifyContent: "center",
    minHeight: "100%",
  },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 18,
    padding: 24,
    shadowColor: "#0f172a",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.08,
    shadowRadius: 16,
    elevation: 3,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginBottom: 8,
  },
  title: {
    fontSize: 22,
    fontWeight: "800",
    color: "#0f172a",
    flex: 1,
  },
  body: {
    color: "#475569",
    fontSize: 14,
    marginBottom: 16,
  },
  label: {
    fontWeight: "700",
    color: "#334155",
    fontSize: 13,
    marginTop: 8,
    marginBottom: 6,
  },
  input: {
    borderWidth: 1,
    borderColor: "#cbd5e1",
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 12,
    fontSize: 14,
    color: "#0f172a",
    backgroundColor: "#ffffff",
    marginBottom: 4,
  },
  primaryBtn: {
    backgroundColor: "#0f766e",
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 18,
  },
  btnDisabled: {
    opacity: 0.6,
  },
  btnInner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  primaryBtnText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 15,
  },
  helperText: {
    color: "#64748b",
    fontSize: 13,
    textAlign: "center",
    marginTop: 16,
    lineHeight: 18,
  },
  errorBox: {
    backgroundColor: "#fef2f2",
    borderColor: "#fecaca",
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
  },
  errorText: {
    color: "#b91c1c",
    fontSize: 13,
  },
});
