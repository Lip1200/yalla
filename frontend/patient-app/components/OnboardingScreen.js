/**
 * OnboardingScreen — first-launch flow for fresh patients (issue #8).
 *
 * Two steps:
 *  1. Welcome — explains Yalla in one screen with a single CTA.
 *  2. Health form — captures the minimum we need to personalize the app
 *     without feeling like a medical exam: age, primary goal, weekly
 *     activity baseline (minutes), privacy level radio.
 *
 * On submit, PATCHes `/api/users/{profileId}` with the collected fields
 * and calls `onComplete(updatedProfile)` so App can hide the gate and
 * load the main shell.
 *
 * Triggering criteria are decided by the parent (App.js) — typically:
 *   profile.age == null && (profile.primary_goal || "") === ""
 */

import { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { ChevronRight, Heart, ShieldCheck, Sparkles, Target } from "lucide-react-native";

import { apiPatch } from "../services/api";

const PRIVACY_OPTIONS = [
  { value: "Partage complet", label: "Partage complet", hint: "Mon médecin voit toutes mes données de suivi." },
  { value: "Partage sélectif", label: "Partage sélectif", hint: "Je choisis ensuite ce que je partage par catégorie." },
  { value: "Données privées", label: "Données privées", hint: "Seules les données médicales restent visibles." },
];

export default function OnboardingScreen({ profileId, profileName, onComplete }) {
  const [step, setStep] = useState(0);
  const [age, setAge] = useState("");
  const [primaryGoal, setPrimaryGoal] = useState("");
  const [privacyLevel, setPrivacyLevel] = useState("Partage sélectif");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    const trimmedGoal = primaryGoal.trim();
    if (!trimmedGoal) {
      Alert.alert("Champ manquant", "Renseigne ton objectif principal pour qu'on puisse personnaliser ton parcours.");
      return;
    }
    const ageInt = age ? parseInt(age, 10) : null;
    if (age && (Number.isNaN(ageInt) || ageInt < 0 || ageInt > 120)) {
      Alert.alert("Âge invalide", "L'âge doit être compris entre 0 et 120.");
      return;
    }
    setSubmitting(true);
    try {
      const updated = await apiPatch(`/api/users/${profileId}`, {
        age: ageInt,
        primary_goal: trimmedGoal,
        privacy_level: privacyLevel,
      });
      onComplete?.(updated);
    } catch (error) {
      Alert.alert("Enregistrement impossible", error.message ?? "Réessaie dans un instant.");
    } finally {
      setSubmitting(false);
    }
  }

  if (step === 0) {
    return (
      <ScrollView contentContainerStyle={styles.shell}>
        <View style={styles.welcomeCard}>
          <View style={styles.iconBubble}>
            <Sparkles size={32} color="#0f766e" />
          </View>
          <Text style={styles.welcomeTitle}>Bienvenue {profileName || ""}!</Text>
          <Text style={styles.welcomeBody}>
            Yalla t'accompagne pour bouger plus, mieux manger et vivre avec sérénité ton parcours diabète.
            Trois minutes pour personnaliser ton expérience et on attaque.
          </Text>

          <View style={styles.bulletRow}>
            <Heart size={20} color="#0f766e" />
            <Text style={styles.bulletText}>Tu choisis ce que tu partages avec ton médecin.</Text>
          </View>
          <View style={styles.bulletRow}>
            <Target size={20} color="#0f766e" />
            <Text style={styles.bulletText}>Tes défis sont calibrés sur ton objectif personnel.</Text>
          </View>
          <View style={styles.bulletRow}>
            <ShieldCheck size={20} color="#0f766e" />
            <Text style={styles.bulletText}>Tu peux activer le mode données privées à tout moment.</Text>
          </View>

          <Pressable onPress={() => setStep(1)} style={styles.primaryButton}>
            <Text style={styles.primaryButtonText}>Continuer</Text>
            <ChevronRight size={18} color="#ffffff" />
          </Pressable>
        </View>
      </ScrollView>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.shell}>
      <View style={styles.welcomeCard}>
        <Text style={styles.welcomeTitle}>Quelques infos pour démarrer</Text>
        <Text style={styles.welcomeBody}>
          Tu peux laisser des champs vides — tu pourras les compléter plus tard depuis ton profil.
        </Text>

        <Text style={styles.label}>Ton âge</Text>
        <TextInput
          style={styles.input}
          value={age}
          onChangeText={setAge}
          placeholder="ex. 47"
          keyboardType="number-pad"
          editable={!submitting}
        />

        <Text style={styles.label}>Ton objectif principal</Text>
        <TextInput
          style={[styles.input, styles.inputMultiline]}
          value={primaryGoal}
          onChangeText={setPrimaryGoal}
          placeholder="ex. Marcher 30 minutes par jour, stabiliser ma glycémie…"
          multiline
          numberOfLines={3}
          editable={!submitting}
        />

        <Text style={styles.label}>Mes préférences de partage</Text>
        {PRIVACY_OPTIONS.map((opt) => {
          const active = privacyLevel === opt.value;
          return (
            <Pressable
              key={opt.value}
              onPress={() => setPrivacyLevel(opt.value)}
              style={[styles.privacyRow, active && styles.privacyRowActive]}
            >
              <Text style={[styles.privacyLabel, active && styles.privacyLabelActive]}>{opt.label}</Text>
              <Text style={styles.privacyHint}>{opt.hint}</Text>
            </Pressable>
          );
        })}

        <Pressable
          onPress={handleSubmit}
          style={[styles.primaryButton, submitting && styles.buttonDisabled]}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <>
              <Text style={styles.primaryButtonText}>Démarrer Yalla</Text>
              <ChevronRight size={18} color="#ffffff" />
            </>
          )}
        </Pressable>

        <Pressable onPress={() => setStep(0)} disabled={submitting}>
          <Text style={styles.backLink}>← Revenir à l'écran de bienvenue</Text>
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
  },
  welcomeCard: {
    backgroundColor: "#ffffff",
    borderRadius: 18,
    padding: 24,
    shadowColor: "#0f172a",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.08,
    shadowRadius: 16,
    elevation: 3,
  },
  iconBubble: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#ecfdf5",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  welcomeTitle: {
    fontSize: 24,
    fontWeight: "800",
    color: "#0f172a",
    marginBottom: 8,
  },
  welcomeBody: {
    fontSize: 14,
    color: "#475569",
    lineHeight: 20,
    marginBottom: 16,
  },
  bulletRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginBottom: 10,
  },
  bulletText: {
    flex: 1,
    fontSize: 14,
    color: "#0f172a",
  },
  label: {
    fontWeight: "700",
    color: "#334155",
    fontSize: 13,
    marginTop: 14,
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
  },
  inputMultiline: {
    minHeight: 70,
    textAlignVertical: "top",
  },
  privacyRow: {
    borderWidth: 1,
    borderColor: "#e2e8f0",
    borderRadius: 10,
    padding: 12,
    marginTop: 8,
  },
  privacyRowActive: {
    borderColor: "#0f766e",
    backgroundColor: "#ecfdf5",
  },
  privacyLabel: {
    fontWeight: "700",
    color: "#0f172a",
    fontSize: 14,
  },
  privacyLabelActive: {
    color: "#0f766e",
  },
  privacyHint: {
    fontSize: 12,
    color: "#475569",
    marginTop: 2,
  },
  primaryButton: {
    backgroundColor: "#0f766e",
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "center",
    gap: 6,
    marginTop: 18,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  primaryButtonText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 15,
  },
  backLink: {
    textAlign: "center",
    color: "#64748b",
    fontSize: 13,
    marginTop: 14,
  },
});
