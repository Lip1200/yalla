/**
 * BadgesSection — display the patient's earned badges + a teaser of the
 * locked ones still to unlock.
 *
 * Issue #38. Consumes the backend from #22:
 *   GET /api/challenges/badges                 — full catalogue
 *   GET /api/challenges/badges/patient/{id}    — what's been earned
 *
 * Renders a horizontal carousel of cards. Earned badges show in full
 * color; locked badges are greyed out with the criteria as a teaser
 * ("Termine 5 défis pour débloquer").
 *
 * Props:
 *   patientId         — int, required
 *   onPress?          — optional handler when a badge is tapped
 *
 * Uses the shared `services/api.js#apiGet` which carries the logged-in
 * patient's bearer token and handles the refresh-on-401 dance.
 */
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Trophy } from "lucide-react-native";

import { apiGet } from "../services/api";

function criterionLabel(badge) {
  const kind = badge?.criteria_kind;
  const n = badge?.criteria_threshold ?? 1;
  const cat = badge?.criteria_category;
  if (kind === "first_completion") return "Termine ton premier défi";
  if (kind === "completion_count") return `Termine ${n} défis`;
  if (kind === "category_completion") return `Termine ${n} défis ${cat}`;
  return "À débloquer";
}

export default function BadgesSection({ patientId, onPress }) {
  const [catalogue, setCatalogue] = useState([]);
  const [earned, setEarned] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const [allBadges, patientBadges] = await Promise.all([
          apiGet("/api/challenges/badges"),
          apiGet(`/api/challenges/badges/patient/${patientId}`),
        ]);
        if (cancelled) return;
        setCatalogue(allBadges ?? []);
        setEarned(patientBadges ?? []);
      } catch (e) {
        if (cancelled) return;
        setError(e?.message ?? "Impossible de charger les badges.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    if (patientId) load();
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  const items = useMemo(() => {
    const earnedById = new Map(
      (earned ?? []).map((pb) => [pb?.badge?.id, pb]),
    );
    return (catalogue ?? []).map((badge) => ({
      badge,
      earned: earnedById.has(badge.id),
      earnedAt: earnedById.get(badge.id)?.earned_at ?? null,
    }));
  }, [catalogue, earned]);

  if (loading) {
    return (
      <View style={styles.section}>
        <View style={styles.headerRow}>
          <Trophy size={18} color="#0f766e" />
          <Text style={styles.title}>Mes badges</Text>
        </View>
        <ActivityIndicator color="#0f766e" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.section}>
        <View style={styles.headerRow}>
          <Trophy size={18} color="#0f766e" />
          <Text style={styles.title}>Mes badges</Text>
        </View>
        <Text style={styles.error}>{error}</Text>
      </View>
    );
  }

  if (items.length === 0) {
    return null;
  }

  const earnedCount = items.filter((i) => i.earned).length;

  return (
    <View style={styles.section}>
      <View style={styles.headerRow}>
        <Trophy size={18} color="#0f766e" />
        <Text style={styles.title}>Mes badges</Text>
        <Text style={styles.counter}>
          {earnedCount}/{items.length}
        </Text>
      </View>
      <FlatList
        data={items}
        keyExtractor={(item) => String(item.badge.id)}
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.row}
        renderItem={({ item }) => (
          <Pressable
            style={[styles.card, !item.earned && styles.cardLocked]}
            onPress={() => onPress?.(item)}
          >
            <Text style={[styles.icon, !item.earned && styles.iconLocked]}>
              {item.badge.icon || "🏅"}
            </Text>
            <Text
              style={[styles.name, !item.earned && styles.nameLocked]}
              numberOfLines={1}
            >
              {item.badge.name}
            </Text>
            <Text style={styles.hint} numberOfLines={2}>
              {item.earned ? item.badge.description : criterionLabel(item.badge)}
            </Text>
          </Pressable>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    paddingVertical: 14,
    paddingHorizontal: 14,
    marginBottom: 16,
    shadowColor: "#0f172a",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 2,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 10,
  },
  title: {
    fontSize: 16,
    fontWeight: "700",
    color: "#0f172a",
    flex: 1,
  },
  counter: {
    fontSize: 13,
    fontWeight: "700",
    color: "#0f766e",
  },
  row: {
    gap: 10,
    paddingVertical: 2,
    paddingRight: 4,
  },
  card: {
    width: 130,
    padding: 12,
    borderRadius: 12,
    backgroundColor: "#ecfdf5",
    borderWidth: 1,
    borderColor: "#bbf7d0",
  },
  cardLocked: {
    backgroundColor: "#f1f5f9",
    borderColor: "#e2e8f0",
    opacity: 0.85,
  },
  icon: {
    fontSize: 30,
    marginBottom: 4,
  },
  iconLocked: {
    opacity: 0.5,
  },
  name: {
    fontWeight: "700",
    color: "#065f46",
    fontSize: 13,
  },
  nameLocked: {
    color: "#64748b",
  },
  hint: {
    fontSize: 11,
    color: "#475569",
    marginTop: 4,
  },
  error: {
    color: "#b91c1c",
    fontSize: 13,
  },
});
