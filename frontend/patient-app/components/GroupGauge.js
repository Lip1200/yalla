/**
 * GroupGauge — visual gauge showing how full a "group" container is.
 *
 * Issue #14. Originally written for restaurant pools (Epic 3) but
 * intentionally generic — works for any (current, target) pair:
 *   • restaurant pool participants  → 3/6 places
 *   • support session enrolment     → 4/10 places
 *   • community group towards a soft cap (if introduced later)
 *
 * Visual: a thin horizontal bar that fills proportionally and shifts
 * color as the gauge approaches full:
 *   <50%   teal      "still room"
 *   50-79% lime      "filling up"
 *   80-99% amber     "nearly there"
 *   100%   green     "complete"
 *
 * Props:
 *   current   — int, ≥ 0
 *   target    — int, ≥ 1
 *   label     — optional, defaults to "membres"
 *   compact   — optional bool, shrinks paddings & font for use in cards
 */
import { StyleSheet, Text, View } from "react-native";

function colorForRatio(ratio) {
  if (ratio >= 1) return "#047857"; // complete
  if (ratio >= 0.8) return "#b45309"; // nearly there
  if (ratio >= 0.5) return "#84cc16"; // filling up
  return "#0f766e"; // still room
}

export default function GroupGauge({ current = 0, target = 1, label = "membres", compact = false }) {
  const safeTarget = Math.max(1, target);
  const safeCurrent = Math.max(0, current);
  const ratio = Math.min(1, safeCurrent / safeTarget);
  const pct = Math.round(ratio * 100);
  const fillColor = colorForRatio(ratio);

  return (
    <View style={[styles.wrap, compact && styles.wrapCompact]}>
      <View style={styles.headerRow}>
        <Text style={[styles.count, compact && styles.countCompact]}>
          {safeCurrent}/{safeTarget}
        </Text>
        <Text style={[styles.label, compact && styles.labelCompact]}>{label}</Text>
        <Text style={[styles.pct, compact && styles.pctCompact, { color: fillColor }]}>
          {pct}%
        </Text>
      </View>
      <View style={[styles.track, compact && styles.trackCompact]}>
        <View
          style={[
            styles.fill,
            { width: `${pct}%`, backgroundColor: fillColor },
          ]}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 8,
    marginBottom: 4,
  },
  wrapCompact: {
    marginTop: 6,
    marginBottom: 2,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "baseline",
    gap: 6,
    marginBottom: 6,
  },
  count: {
    fontSize: 16,
    fontWeight: "800",
    color: "#0f172a",
  },
  countCompact: {
    fontSize: 14,
  },
  label: {
    fontSize: 13,
    color: "#475569",
    flex: 1,
  },
  labelCompact: {
    fontSize: 11,
  },
  pct: {
    fontSize: 13,
    fontWeight: "700",
  },
  pctCompact: {
    fontSize: 11,
  },
  track: {
    height: 8,
    borderRadius: 999,
    backgroundColor: "#e2e8f0",
    overflow: "hidden",
  },
  trackCompact: {
    height: 6,
  },
  fill: {
    height: "100%",
    borderRadius: 999,
  },
});
