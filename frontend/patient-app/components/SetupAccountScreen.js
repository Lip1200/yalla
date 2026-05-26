/**
 * SetupAccountScreen — finalize a patient account created by a doctor.
 *
 * Issue #37. Consumes the invitation URL flow built by issue #33:
 *
 *   doctor creates patient account → backend returns invitation_url
 *   `${FRONTEND_BASE_URL}/setup?token=XXX`
 *   patient opens that URL (out-of-band) → this screen
 *   patient picks a password → POST /api/auth/setup-password { token, password }
 *   backend creates the auth user, links it to the pre-provisioned profile,
 *   returns an AuthSession → we store it locally for #28 to consume.
 *
 * Two ways to get a token into this screen:
 *   1. The app was opened with a `?token=XXX` URL (deep link). The parent
 *      reads `Linking.useURL()` and passes `initialToken` here.
 *   2. The patient pastes the invitation URL or the bare token manually
 *      into the input field below.
 */
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { CheckCircle, KeyRound, Mail, ShieldCheck } from "lucide-react-native";

import { API_BASE_URL } from "../services/api";
import { saveSession } from "../services/auth";

function parseTokenFromInput(value) {
  if (!value) return "";
  const trimmed = value.trim();
  // Accept both the bare token and a full invitation URL
  // (e.g. https://app.yalla/setup?token=XXXX or yalla://setup?token=XXXX).
  const tokenMatch = trimmed.match(/[?&]token=([^&\s]+)/);
  if (tokenMatch) return tokenMatch[1];
  return trimmed;
}

export default function SetupAccountScreen({ initialToken = "", onDone }) {
  const [tokenInput, setTokenInput] = useState(initialToken);
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(null); // {email, full_name} on success

  useEffect(() => {
    if (initialToken && initialToken !== tokenInput) {
      setTokenInput(initialToken);
    }
  }, [initialToken]);

  async function handleSubmit() {
    setError("");
    const token = parseTokenFromInput(tokenInput);
    if (!token) {
      setError("Le lien d'invitation est vide.");
      return;
    }
    if (password.length < 8) {
      setError("Le mot de passe doit comporter au moins 8 caractères.");
      return;
    }
    if (password !== passwordConfirm) {
      setError("Les deux mots de passe ne correspondent pas.");
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/setup-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      const body = await response.json().catch(() => ({}));

      if (response.status === 404) {
        throw new Error("Lien d'invitation introuvable. Vérifie l'URL ou demande un nouveau lien à ton médecin.");
      }
      if (response.status === 400) {
        throw new Error(body.detail ?? "Lien d'invitation déjà utilisé.");
      }
      if (response.status === 410) {
        throw new Error("Lien d'invitation expiré. Demande un nouveau lien à ton médecin.");
      }
      if (response.status === 202) {
        // Email confirmation required by Supabase
        setSuccess({
          email: body.email ?? "ton email",
          full_name: body.full_name ?? "",
          needsConfirmation: true,
        });
        return;
      }
      if (!response.ok) {
        throw new Error(body.detail ?? "Création du compte impossible.");
      }

      // Success — store the session for future #28 wiring and show
      // the confirmation card.
      await saveSession(body);
      setSuccess({
        email: body?.user?.email ?? "—",
        full_name: body?.user?.full_name ?? "",
        needsConfirmation: false,
      });
    } catch (e) {
      setError(e?.message ?? "Erreur inattendue.");
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <ScrollView contentContainerStyle={styles.shell}>
        <View style={styles.card}>
          <View style={styles.headerRow}>
            <CheckCircle size={28} color="#047857" />
            <Text style={styles.title}>Compte activé !</Text>
          </View>
          <Text style={styles.body}>
            Bienvenue {success.full_name || ""} 👋
          </Text>
          <Text style={styles.body}>Email : {success.email}</Text>
          {success.needsConfirmation ? (
            <Text style={[styles.body, { color: "#92400e" }]}>
              ⚠️ Pense à confirmer ton email via le message envoyé par Yalla avant de te connecter.
            </Text>
          ) : (
            <Text style={styles.body}>
              Tu peux maintenant utiliser l'application avec ton mot de passe.
            </Text>
          )}
          <Pressable style={styles.primaryBtn} onPress={onDone}>
            <Text style={styles.primaryBtnText}>Continuer vers Yalla</Text>
          </Pressable>
        </View>
      </ScrollView>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.shell}>
      <View style={styles.card}>
        <View style={styles.headerRow}>
          <ShieldCheck size={28} color="#0f766e" />
          <Text style={styles.title}>Activer mon compte</Text>
        </View>
        <Text style={styles.body}>
          Ton médecin t'a créé un compte Yalla. Choisis ton mot de passe pour finaliser l'activation.
        </Text>

        <Text style={styles.label}>Lien d'invitation reçu</Text>
        <TextInput
          placeholder="Colle l'URL d'invitation ou le token"
          placeholderTextColor="#94a3b8"
          value={tokenInput}
          onChangeText={setTokenInput}
          style={styles.input}
          autoCapitalize="none"
          autoCorrect={false}
          editable={!submitting}
        />

        <Text style={styles.label}>Nouveau mot de passe</Text>
        <TextInput
          placeholder="8 caractères minimum"
          placeholderTextColor="#94a3b8"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          style={styles.input}
          editable={!submitting}
        />

        <Text style={styles.label}>Confirmation du mot de passe</Text>
        <TextInput
          placeholder="Saisis-le à nouveau"
          placeholderTextColor="#94a3b8"
          value={passwordConfirm}
          onChangeText={setPasswordConfirm}
          secureTextEntry
          style={styles.input}
          editable={!submitting}
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Pressable
          style={[styles.primaryBtn, submitting && styles.btnDisabled]}
          onPress={handleSubmit}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text style={styles.primaryBtnText}>Activer mon compte</Text>
          )}
        </Pressable>

        {onDone ? (
          <Pressable style={styles.linkBtn} onPress={onDone}>
            <Text style={styles.linkText}>Annuler et revenir à l'app</Text>
          </Pressable>
        ) : null}
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
    marginBottom: 12,
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
    marginBottom: 12,
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
    marginTop: 16,
  },
  btnDisabled: {
    opacity: 0.6,
  },
  primaryBtnText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 15,
  },
  error: {
    color: "#b91c1c",
    fontSize: 13,
    marginTop: 10,
    marginBottom: 6,
  },
  linkBtn: {
    alignItems: "center",
    marginTop: 10,
  },
  linkText: {
    color: "#64748b",
    fontSize: 13,
  },
});
