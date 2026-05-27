/**
 * ProgressScreen — Défis tab. Stats row, pedometer card, badges, then
 * 'Mes défis' (active assignments from the backend) and a 'Rejoindre un
 * défi' carousel filtered against locally-tracked joinedChallengeIds.
 */

import { Plus } from "lucide-react-native";
import { ScrollView, View } from "react-native";

import BadgesSection from "../components/BadgesSection";
import PedometerCard from "../components/PedometerCard";
import { Pressable, StatCard, Text } from "../components/atoms";
import { styles } from "../styles";
import { formatDate } from "../utils";

function ChallengeCard({ challenge }) {
  const progress = typeof challenge.progress === "number" ? challenge.progress : 0;
  const dueLabel = challenge.due_on ? `· échéance ${formatDate(challenge.due_on)}` : "";
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>{challenge.title}</Text>
      <Text style={styles.cardMeta}>{challenge.category}</Text>
      <Text style={styles.cardBody}>{challenge.description}</Text>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: `${progress}%` }]} />
      </View>
      <Text style={styles.cardFooter}>
        {progress}% {dueLabel}
      </Text>
    </View>
  );
}

export default function ProgressScreen({
  joinedChallengeIds,
  onJoinChallenge,
  progression,
  patientId,
  availableChallenges,
}) {
  // progression.active_challenges is the source of truth (refreshed from
  // DB after joinChallenge). joinedChallengeIds is kept locally as a
  // fast filter for the 'Rejoindre un défi' carousel between click and
  // refresh.
  const availableSuggestions = availableChallenges.filter(
    (challenge) => !joinedChallengeIds.has(challenge.id),
  );
  const activeChallenges = progression.active_challenges;

  return (
    <ScrollView contentContainerStyle={styles.listContent}>
      <View style={styles.statsRow}>
        <StatCard label="Minutes" value={progression.weekly_activity_minutes} />
        <StatCard label="Défis" value={`${progression.challenge_completion_rate}%`} />
        <StatCard label="Série" value={`${progression.current_streak_days}j`} />
      </View>

      <PedometerCard patientId={patientId} />

      <BadgesSection patientId={patientId} />

      <Text style={styles.sectionTitle}>Mes défis</Text>
      {activeChallenges.map((challenge) => (
        <ChallengeCard key={challenge.id} challenge={challenge} />
      ))}

      <Text style={styles.sectionTitle}>Rejoindre un défi</Text>
      {availableSuggestions.map((challenge) => (
        <View key={challenge.id} style={styles.card}>
          <View style={styles.cardHeader}>
            <View style={styles.flex}>
              <Text style={styles.cardTitle}>{challenge.title}</Text>
              <Text style={styles.cardMeta}>{challenge.category}</Text>
            </View>
            <Pressable onPress={() => onJoinChallenge(challenge)} style={styles.iconButton}>
              <Plus size={18} color="#ffffff" />
            </Pressable>
          </View>
          <Text style={styles.cardBody}>{challenge.description}</Text>
          {challenge.due_on ? (
            <Text style={styles.cardFooter}>Échéance {formatDate(challenge.due_on)}</Text>
          ) : null}
        </View>
      ))}
    </ScrollView>
  );
}
