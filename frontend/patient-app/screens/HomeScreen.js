/**
 * HomeScreen — landing tab. Hero card with the patient's main goal, two
 * mini stats (weekly minutes, challenge %), and a card teasing the next
 * active challenge with a CTA jumping to the Progress tab.
 */

import { ScrollView, View } from "react-native";

import { MiniStat, Pressable, Text } from "../components/atoms";
import { styles } from "../styles";

export default function HomeScreen({ progression, profile, setActiveTab }) {
  if (!progression || !profile) {
    return (
      <ScrollView contentContainerStyle={styles.listContent}>
        <View style={styles.heroCard}>
          <Text style={styles.heroKicker}>En attente de données</Text>
          <Text style={styles.heroText}>
            Impossible de charger ton tableau de bord. Tire pour rafraîchir ou reconnecte-toi.
          </Text>
        </View>
      </ScrollView>
    );
  }
  const nextChallenge = progression.active_challenges[0];

  return (
    <ScrollView contentContainerStyle={styles.listContent}>
      <View style={styles.heroCard}>
        <Text style={styles.heroKicker}>Objectif du moment</Text>
        <Text style={styles.heroText}>{profile.main_goal}</Text>
        <View style={styles.heroStats}>
          <MiniStat label="minutes" value={profile.weekly_activity_minutes} />
          <MiniStat label="défis" value={`${profile.challenge_completion_rate}%`} />
        </View>
      </View>

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Aujourd'hui</Text>
        <Pressable onPress={() => setActiveTab("progress")}>
          <Text style={styles.linkText}>Voir défis</Text>
        </Pressable>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>{nextChallenge?.title ?? "Choisir un défi"}</Text>
        <Text style={styles.cardBody}>
          {nextChallenge?.description ?? "Rejoins un défi simple pour garder le rythme cette semaine."}
        </Text>
        {nextChallenge ? (
          <>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${nextChallenge.progress}%` }]} />
            </View>
            <Text style={styles.cardFooter}>{nextChallenge.progress}% terminé</Text>
          </>
        ) : null}
      </View>
    </ScrollView>
  );
}
