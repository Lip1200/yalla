import { useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  Text,
  TextInput,
  View,
} from "react-native";
import { LogIn, UserPlus } from "lucide-react";

import { login, signup } from "./auth";
import YALLA_LOGO from "./assets/yalla-logo.png";

const HOSPITAL_OPTIONS = [
  "HUG - Hôpitaux universitaires de Genève",
  "Clinique La Colline",
  "Clinique Générale-Beaulieu",
  "Clinique des Grangettes",
  "Clinique de Carouge",
  "Centre médical de Plainpalais",
];

const styles = {
  shell: {
    flex: 1,
    minHeight: "100vh",
    backgroundColor: "#f5f7f8",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 32,
    paddingHorizontal: 16,
  },
  card: {
    width: "100%",
    maxWidth: 420,
    backgroundColor: "#ffffff",
    borderRadius: 16,
    paddingVertical: 32,
    paddingHorizontal: 28,
    shadowColor: "#0f172a",
    shadowOffset: { width: 0, height: 16 },
    shadowOpacity: 0.08,
    shadowRadius: 32,
  },
  brand: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginBottom: 20,
  },
  brandName: {
    fontSize: 20,
    fontWeight: "700",
    color: "#0f172a",
  },
  brandMeta: {
    fontSize: 13,
    color: "#64748b",
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: "#0f172a",
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: "#475569",
    marginBottom: 20,
  },
  fieldLabel: {
    fontSize: 13,
    fontWeight: "600",
    color: "#334155",
    marginBottom: 6,
  },
  input: {
    borderWidth: 1,
    borderColor: "#cbd5e1",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: "#0f172a",
    marginBottom: 14,
    backgroundColor: "#ffffff",
  },
  primaryButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#0f766e",
    paddingVertical: 12,
    borderRadius: 10,
    marginTop: 4,
  },
  primaryButtonText: {
    color: "#f8fafc",
    fontWeight: "600",
    fontSize: 15,
  },
  switchRow: {
    marginTop: 16,
    alignItems: "center",
  },
  switchText: {
    color: "#64748b",
    fontSize: 13,
  },
  switchLink: {
    color: "#0f766e",
    fontWeight: "600",
  },
  optionRow: {
    gap: 8,
    marginBottom: 14,
  },
  dropdownButton: {
    borderWidth: 1,
    borderColor: "#cbd5e1",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: "#ffffff",
    marginBottom: 8,
  },
  dropdownButtonText: {
    color: "#0f172a",
    fontSize: 14,
    fontWeight: "600",
  },
  optionChip: {
    borderWidth: 1,
    borderColor: "#cbd5e1",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 9,
    backgroundColor: "#ffffff",
  },
  optionChipActive: {
    borderColor: "#0f766e",
    backgroundColor: "#ecfdf5",
  },
  optionChipText: {
    color: "#334155",
    fontSize: 13,
    fontWeight: "600",
  },
  optionChipTextActive: {
    color: "#0f766e",
  },
  errorBox: {
    backgroundColor: "#fef2f2",
    borderColor: "#fecaca",
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginBottom: 16,
  },
  errorText: {
    color: "#b91c1c",
    fontSize: 13,
  },
  successBox: {
    backgroundColor: "#ecfdf5",
    borderColor: "#bbf7d0",
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginBottom: 16,
  },
  successText: {
    color: "#047857",
    fontSize: 13,
  },
};

export default function LoginScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login"); // 'login' | 'signup'
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [specialty, setSpecialty] = useState("Endocrinologie et diabétologie");
  const [facility, setFacility] = useState(HOSPITAL_OPTIONS[0]);
  const [facilityOpen, setFacilityOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  async function handleSubmit() {
    setError("");
    setInfo("");

    if (!email.trim() || !password) {
      setError("Email et mot de passe sont requis.");
      return;
    }
    if (mode === "signup" && !fullName.trim()) {
      setError("Le nom complet est requis pour l'inscription.");
      return;
    }
    if (mode === "signup" && !facility.trim()) {
      setError("Choisissez un établissement.");
      return;
    }

    setSubmitting(true);
    try {
      if (mode === "login") {
        const session = await login(email.trim(), password);
        onAuthenticated(session);
      } else {
        const result = await signup(email.trim(), password, fullName.trim(), specialty.trim(), facility.trim());
        if (result?.access_token) {
          onAuthenticated(result);
        } else {
          setInfo("Inscription enregistrée. Vérifiez vos emails pour confirmer le compte avant de vous connecter.");
          setMode("login");
        }
      }
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting(false);
    }
  }

  const isLogin = mode === "login";

  return (
    <View style={styles.shell}>
      <View style={styles.card}>
        <View style={styles.brand}>
          <YallaLogo />
          <View>
            <Text style={styles.brandName}>Yalla</Text>
            <Text style={styles.brandMeta}>Espace médecin</Text>
          </View>
        </View>

        <Text style={styles.title}>{isLogin ? "Connexion" : "Créer un compte"}</Text>
        <Text style={styles.subtitle}>
          {isLogin
            ? "Connectez-vous pour accéder à votre tableau de bord patients."
            : "Inscrivez-vous pour configurer votre espace médecin."}
        </Text>

        {error ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}
        {info ? (
          <View style={styles.successBox}>
            <Text style={styles.successText}>{info}</Text>
          </View>
        ) : null}

        {!isLogin ? (
          <>
            <Text style={styles.fieldLabel}>Nom complet</Text>
            <TextInput
              style={styles.input}
              value={fullName}
              onChangeText={setFullName}
              placeholder="Dr. Nadia Benali"
              autoCapitalize="words"
            />
          </>
        ) : null}

        {!isLogin ? (
          <>
            <Text style={styles.fieldLabel}>Spécialité</Text>
            <TextInput
              style={styles.input}
              value={specialty}
              onChangeText={setSpecialty}
              placeholder="Endocrinologie et diabétologie"
            />

            <Text style={styles.fieldLabel}>Établissement</Text>
            <Pressable style={styles.dropdownButton} onPress={() => setFacilityOpen((open) => !open)}>
              <Text style={styles.dropdownButtonText}>{facility}</Text>
            </Pressable>
            {facilityOpen ? (
              <View style={styles.optionRow}>
                {HOSPITAL_OPTIONS.map((hospital) => (
                  <Pressable
                    key={hospital}
                    onPress={() => {
                      setFacility(hospital);
                      setFacilityOpen(false);
                    }}
                    style={[styles.optionChip, facility === hospital && styles.optionChipActive]}
                  >
                    <Text style={[styles.optionChipText, facility === hospital && styles.optionChipTextActive]}>
                      {hospital}
                    </Text>
                  </Pressable>
                ))}
              </View>
            ) : null}
          </>
        ) : null}

        <Text style={styles.fieldLabel}>Email</Text>
        <TextInput
          style={styles.input}
          value={email}
          onChangeText={setEmail}
          placeholder="email@example.com"
          autoCapitalize="none"
          keyboardType="email-address"
        />

        <Text style={styles.fieldLabel}>Mot de passe</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          placeholder={isLogin ? "Votre mot de passe" : "8 caractères minimum"}
          secureTextEntry
        />

        <Pressable
          style={styles.primaryButton}
          onPress={handleSubmit}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#f8fafc" />
          ) : isLogin ? (
            <>
              <LogIn size={18} color="#f8fafc" />
              <Text style={styles.primaryButtonText}>Se connecter</Text>
            </>
          ) : (
            <>
              <UserPlus size={18} color="#f8fafc" />
              <Text style={styles.primaryButtonText}>S'inscrire</Text>
            </>
          )}
        </Pressable>

        <View style={styles.switchRow}>
          <Text style={styles.switchText}>
            {isLogin ? "Pas encore de compte ?" : "Déjà inscrit ?"}{" "}
            <Text
              style={styles.switchLink}
              onPress={() => {
                setMode(isLogin ? "signup" : "login");
                setError("");
                setInfo("");
              }}
            >
              {isLogin ? "Créer un compte" : "Se connecter"}
            </Text>
          </Text>
        </View>
      </View>
    </View>
  );
}

function YallaLogo() {
  return <Image source={YALLA_LOGO} style={{ width: 48, height: 48, borderRadius: 24 }} />;
}
