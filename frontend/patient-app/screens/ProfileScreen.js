/**
 * ProfileScreen — issue #9. Reached by tapping the top header. Shows
 * the patient's avatar (initials), name, role, primary goal, stats row,
 * last check-in card, and badges. Buttons to go back home or log out.
 */

import { ScrollView, View } from "react-native";

import BadgesSection from "../components/BadgesSection";
import { Pressable, StatCard, Text } from "../components/atoms";
import { styles } from "../styles";
import { formatDate } from "../utils";

export default function ProfileScreen({ profile, progression, patientId, isExpert, onClose, onLogout }) {
  if (!profile) return null;
  const initials = (profile.full_name || "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
  const roleLabel = isExpert ? "Patient expert" : profile.role === "doctor" ? "Médecin" : "Patient";
  const checkInLabel = profile.last_check_in ? formatDate(profile.last_check_in) : "Aucun depuis l'inscription";
  return (
    <ScrollView contentContainerStyle={styles.listContent}>
      <View style={styles.profileHero}>
        <View style={styles.profileAvatar}>
          <Text style={styles.profileAvatarText}>{initials}</Text>
        </View>
        <Text style={styles.profileName}>{profile.full_name}</Text>
        <Text style={styles.profileRole}>{roleLabel}</Text>
        {profile.primary_goal ? (
          <Text style={styles.profileGoal}>« {profile.primary_goal} »</Text>
        ) : null}
      </View>

      <Text style={styles.sectionTitle}>Mes statistiques</Text>
      <View style={styles.statsRow}>
        <StatCard label="Minutes/semaine" value={progression?.weekly_activity_minutes ?? 0} />
        <StatCard label="Défis %" value={`${progression?.challenge_completion_rate ?? 0}%`} />
        <StatCard label="Série" value={`${progression?.current_streak_days ?? 0}j`} />
      </View>

      <View style={styles.card}>
        <Text style={styles.cardMeta}>Dernier check-in</Text>
        <Text style={styles.cardTitle}>{checkInLabel}</Text>
        <Text style={styles.cardMeta} numberOfLines={1}>Statut : {profile.status || "En progrès"}</Text>
        <Text style={styles.cardMeta}>Confidentialité : {profile.privacy_level || "Données limitées"}</Text>
      </View>

      <BadgesSection patientId={patientId} />

      <Pressable onPress={onClose} style={[styles.secondaryButton, { marginTop: 8 }]}>
        <Text style={styles.secondaryButtonText}>Retour à l'accueil</Text>
      </Pressable>
      <Pressable onPress={onLogout} style={[styles.secondaryButton, { marginTop: 8, borderColor: "#fecaca" }]}>
        <Text style={[styles.secondaryButtonText, { color: "#b91c1c" }]}>Se déconnecter</Text>
      </Pressable>
    </ScrollView>
  );
}
