/**
 * AccessScreen — Services sub-tab. Global privacy mode + per-flag
 * toggles (share_activity, share_challenges, share_restaurants,
 * share_posts, share_messages_with_expert).
 *
 * All five flags are persisted via PATCH /api/patients/{id}/settings/access
 * (migrations 016 + 017).
 */

import { ScrollView, Switch, View } from "react-native";

import { Text } from "../components/atoms";
import { styles } from "../styles";

function AccessToggle({ description, label, onToggle, value }) {
  return (
    <View style={styles.card}>
      <View style={styles.settingRow}>
        <View style={styles.settingText}>
          <Text style={styles.settingTitle}>{label}</Text>
          <Text style={styles.cardMeta}>{description}</Text>
        </View>
        <Switch value={value} onValueChange={onToggle} thumbColor={value ? "#0f766e" : "#f8fafc"} />
      </View>
    </View>
  );
}

export default function AccessScreen({ accessSettings, onToggleAccess, onUpdatePrivacy, settings }) {
  const isPrivate = settings.profile.privacy_level === "Données privées";

  return (
    <ScrollView contentContainerStyle={styles.innerListContent}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Confidentialité</Text>
        <Text style={styles.cardBody}>
          Choisis exactement ce que tu partages avec le médecin et le patient expert.
        </Text>
        <View style={styles.settingRow}>
          <View style={styles.settingText}>
            <Text style={styles.settingTitle}>Mode privé global</Text>
            <Text style={styles.cardMeta}>Désactive les partages principaux sans supprimer les choix fins.</Text>
          </View>
          <Switch value={isPrivate} onValueChange={onUpdatePrivacy} thumbColor={isPrivate ? "#0f766e" : "#f8fafc"} />
        </View>
      </View>

      <AccessToggle
        description="Minutes d'activité, série et progression générale."
        label="Activité physique"
        onToggle={() => onToggleAccess("share_activity")}
        value={accessSettings.share_activity}
      />
      <AccessToggle
        description="Défis rejoints, progression et badges."
        label="Défis"
        onToggle={() => onToggleAccess("share_challenges")}
        value={accessSettings.share_challenges}
      />
      <AccessToggle
        description="Restaurants consultés ou recommandés."
        label="Restaurants"
        onToggle={() => onToggleAccess("share_restaurants")}
        value={accessSettings.share_restaurants}
      />
      <AccessToggle
        description="Posts, commentaires et likes dans la communauté."
        label="Activité sociale"
        onToggle={() => onToggleAccess("share_posts")}
        value={accessSettings.share_posts}
      />
      <AccessToggle
        description="Autoriser le patient expert a voir le contexte des conversations."
        label="Messages avec expert"
        onToggle={() => onToggleAccess("share_messages_with_expert")}
        value={accessSettings.share_messages_with_expert}
      />
    </ScrollView>
  );
}
