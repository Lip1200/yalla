/**
 * LoginScreen — patient-app authentication entry point.
 *
 * Issue #28. Toggleable between login and signup modes. Calls
 * /api/auth/login or /api/auth/signup/patient via services/auth.js,
 * which automatically stores the session in SecureStore and primes the
 * api.js access-token cache.
 *
 * On success: calls `onAuthenticated(session)` so the parent (App.js)
 * can decide to drop the auth shell and load the main app.
 *
 * The patient that received an invitation URL doesn't pass through
 * this screen — they go through SetupAccountScreen (#37) which also
 * lands them with a session.
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
import { LogIn, ShieldCheck, UserPlus } from "lucide-react-native";

import { loginPatient, signupPatient } from "../services/auth";

export default function LoginScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const isLogin = mode === "login";

  function switchMode() {
    setMode(isLogin ? "signup" : "login");
    setError("");
    setInfo("");
  }

  async function handleSubmit() {
    setError("");
    setInfo("");

    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password) {
      setError("Email et mot de passe sont requis.");
      return;
    }
    if (!isLogin) {
      if (!fullName.trim()) {
        setError("Le nom complet est requis pour s'inscrire.");
        return;
      }
      if (password.length < 8) {
        setError("Le mot de passe doit comporter au moins 8 caractères.");
        return;
      }
    }

    setSubmitting(true);
    try {
      if (isLogin) {
        const session = await loginPatient(trimmedEmail, password);
        onAuthenticated?.(session);
      } else {
        const result = await signupPatient(trimmedEmail, password, fullName.trim());
        if (result?.access_token) {
          onAuthenticated?.(result);
        } else {
          setInfo(
            "Compte créé. Confirme ton email via le message que Yalla vient de t'envoyer, puis reviens te connecter.",
          );
          setMode("login");
          setPassword("");
        }
      }
    } catch (e) {
      const status = e?.status;
      if (status === 401) {
        setError("Identifiants invalides. Vérifie l'email et le mot de passe.");
      } else if (status === 400 && /already registered/i.test(e?.message ?? "")) {
        setError("Cet email est déjà enregistré. Connecte-toi à la place.");
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
          <Text style={styles.title}>{isLogin ? "Connexion" : "Inscription"}</Text>
        </View>
        <Text style={styles.body}>
          {isLogin
            ? "Connecte-toi pour retrouver tes défis, ton suivi et ta communauté."
            : "Crée ton compte patient Yalla. Tu pourras te connecter aussitôt si la confirmation email est désactivée."}
        </Text>

        {error ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}
        {info ? (
          <View style={styles.infoBox}>
            <Text style={styles.infoText}>{info}</Text>
          </View>
        ) : null}

        {!isLogin ? (
          <>
            <Text style={styles.label}>Nom complet</Text>
            <TextInput
              style={styles.input}
              value={fullName}
              onChangeText={setFullName}
              placeholder="Karim El Mansouri"
              autoCapitalize="words"
              editable={!submitting}
            />
          </>
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
          placeholder={isLogin ? "Ton mot de passe" : "8 caractères minimum"}
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
          ) : isLogin ? (
            <View style={styles.btnInner}>
              <LogIn size={18} color="#ffffff" />
              <Text style={styles.primaryBtnText}>Se connecter</Text>
            </View>
          ) : (
            <View style={styles.btnInner}>
              <UserPlus size={18} color="#ffffff" />
              <Text style={styles.primaryBtnText}>S'inscrire</Text>
            </View>
          )}
        </Pressable>

        <Pressable style={styles.linkRow} onPress={switchMode}>
          <Text style={styles.linkText}>
            {isLogin ? "Pas encore de compte ? " : "Déjà inscrit ? "}
            <Text style={styles.linkAccent}>
              {isLogin ? "Créer un compte" : "Se connecter"}
            </Text>
          </Text>
        </Pressable>
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
  linkRow: {
    alignItems: "center",
    marginTop: 14,
  },
  linkText: {
    color: "#64748b",
    fontSize: 13,
  },
  linkAccent: {
    color: "#0f766e",
    fontWeight: "700",
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
  infoBox: {
    backgroundColor: "#ecfdf5",
    borderColor: "#bbf7d0",
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
  },
  infoText: {
    color: "#047857",
    fontSize: 13,
  },
});
