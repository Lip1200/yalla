/**
 * SessionsScreen — accompaniment slots scheduled by an expert patient
 * for regular patients to join. The 'Organiser une séance' form is
 * gated behind isExpert; regular patients only see the join CTA on
 * each card.
 */

import { ScrollView, Switch, TextInput, View } from "react-native";

import GroupGauge from "../components/GroupGauge";
import { Pressable, Text } from "../components/atoms";
import { styles } from "../styles";
import { formatDate } from "../utils";

export default function SessionsScreen({
  sessions,
  sessionTitle, setSessionTitle,
  sessionKind, setSessionKind,
  sessionDate, setSessionDate,
  sessionCapacity, setSessionCapacity,
  sessionNotes, setSessionNotes,
  joinedSessions,
  onCreateSession,
  onJoinSession,
  isExpert,
}) {
  return (
    <ScrollView contentContainerStyle={styles.listContent}>
      {isExpert && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Organiser une séance</Text>
          <TextInput
            onChangeText={setSessionTitle}
            placeholder="Titre de la séance"
            placeholderTextColor="#94a3b8"
            style={styles.input}
            value={sessionTitle}
          />
          <View style={[styles.settingRow, { marginTop: 10, marginBottom: 10 }]}>
            <View style={styles.settingText}>
              <Text style={styles.cardMeta}>{sessionKind === "group" ? "Groupe" : "Individuel"}</Text>
            </View>
            <Switch
              value={sessionKind === "group"}
              onValueChange={(val) => setSessionKind(val ? "group" : "individual")}
              thumbColor={sessionKind === "group" ? "#0f766e" : "#f8fafc"}
            />
          </View>
          <TextInput
            onChangeText={setSessionDate}
            placeholder="Date (ex: 2026-06-15T14:00:00)"
            placeholderTextColor="#94a3b8"
            style={styles.input}
            value={sessionDate}
          />
          <TextInput
            onChangeText={setSessionCapacity}
            placeholder="Capacité (ex: 10)"
            placeholderTextColor="#94a3b8"
            style={styles.input}
            keyboardType="numeric"
            value={sessionCapacity}
          />
          <TextInput
            onChangeText={setSessionNotes}
            placeholder="Notes (optionnel)"
            placeholderTextColor="#94a3b8"
            style={[styles.input, { height: 60 }]}
            multiline
            value={sessionNotes}
          />
          <Pressable onPress={onCreateSession} style={styles.primaryButton}>
            <Text style={styles.primaryButtonText}>Créer la séance</Text>
          </Pressable>
        </View>
      )}

      {sessions.map((session) => {
        const isFull = session.enrolled_count >= session.capacity;
        const hasJoined = joinedSessions.has(session.id);

        return (
          <View key={session.id} style={styles.card}>
            <Text style={styles.cardTitle}>{session.title}</Text>
            <Text style={styles.cardMeta}>
              {session.kind === "group" ? "Groupe" : "Individuel"}
            </Text>
            <GroupGauge
              current={session.enrolled_count}
              target={session.capacity}
              label="places"
              compact
            />
            <Text style={styles.cardBody}>{session.notes}</Text>
            <Text style={styles.cardFooter}>{formatDate(session.scheduled_for)}</Text>

            {!isExpert && (
              <Pressable
                onPress={() => onJoinSession(session.id)}
                style={[
                  styles.primaryButton,
                  { marginTop: 12 },
                  (hasJoined || isFull) && { backgroundColor: "#94a3b8" },
                ]}
                disabled={hasJoined || isFull}
              >
                <Text style={styles.primaryButtonText}>
                  {hasJoined ? "Inscrit" : isFull ? "Complet" : "Rejoindre"}
                </Text>
              </Pressable>
            )}
          </View>
        );
      })}
    </ScrollView>
  );
}
