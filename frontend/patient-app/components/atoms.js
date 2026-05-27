/**
 * Atomic components shared across screens. Extracted from App.js as the
 * first step of the #40 split.
 *
 * - `Text`     : drop-in replacement for react-native's Text that picks
 *                a font-family based on the consumer's fontWeight /
 *                fontSize so we get Inter/Outfit consistency without
 *                every callsite spelling it out.
 * - `Pressable`: react-native's Pressable plus a press-down spring
 *                scale animation. Same prop API.
 * - `Skeleton` / `ScreenSkeleton`: shimmering placeholders shown while
 *                loadApp() is running.
 * - `MiniStat` / `StatCard` / `YallaLogo`: trivial display helpers.
 */

import { useEffect, useRef } from "react";
import {
  Animated,
  Image,
  Pressable as RNPressable,
  StyleSheet,
  Text as RNText,
  View,
} from "react-native";

import { styles } from "../styles";

const YALLA_LOGO = require("../assets/yalla-logo.png");

export function Text(props) {
  const { style, ...otherProps } = props;
  let fontFamily = "Inter_400Regular";

  const flatStyle = StyleSheet.flatten(style) || {};
  const weight = flatStyle.fontWeight;

  if (weight === "900" || weight === "800" || weight === "bold") {
    fontFamily = "Outfit_700Bold";
  } else if (weight === "700" || weight === "600") {
    fontFamily = "Outfit_600SemiBold";
  } else if (weight === "500") {
    fontFamily = "Inter_500Medium";
  } else if (flatStyle.fontSize && flatStyle.fontSize >= 16) {
    fontFamily = "Outfit_400Regular";
  }

  return <RNText style={[{ fontFamily }, style]} {...otherProps} />;
}

export function Pressable({ onPress, onPressIn, onPressOut, style, children, ...props }) {
  const scale = useRef(new Animated.Value(1)).current;

  const handlePressIn = (e) => {
    Animated.spring(scale, {
      toValue: 0.95,
      useNativeDriver: true,
      speed: 20,
      bounciness: 10,
    }).start();
    if (onPressIn) onPressIn(e);
  };

  const handlePressOut = (e) => {
    Animated.spring(scale, {
      toValue: 1,
      useNativeDriver: true,
      speed: 20,
      bounciness: 10,
    }).start();
    if (onPressOut) onPressOut(e);
  };

  return (
    <RNPressable
      onPress={onPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      style={style}
      {...props}
    >
      <Animated.View style={{ transform: [{ scale }] }}>{children}</Animated.View>
    </RNPressable>
  );
}

export function Skeleton({ width, height, borderRadius = 8, style }) {
  const anim = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(anim, { toValue: 0.7, duration: 800, useNativeDriver: true }),
        Animated.timing(anim, { toValue: 0.3, duration: 800, useNativeDriver: true }),
      ]),
    ).start();
  }, [anim]);

  return (
    <Animated.View
      style={[
        {
          width,
          height,
          borderRadius,
          backgroundColor: "#e2e8f0",
          opacity: anim,
        },
        style,
      ]}
    />
  );
}

export function ScreenSkeleton({ activeTab }) {
  if (activeTab === "home") {
    return (
      <View style={{ padding: 20, gap: 24 }}>
        <View style={{ gap: 12 }}>
          <Skeleton width={120} height={16} />
          <Skeleton width="100%" height={100} borderRadius={16} />
        </View>
        <View style={{ gap: 12 }}>
          <Skeleton width={150} height={20} />
          <Skeleton width="100%" height={140} borderRadius={16} />
        </View>
      </View>
    );
  }
  if (activeTab === "community") {
    return (
      <View style={{ padding: 20, gap: 16 }}>
        <Skeleton width="100%" height={60} borderRadius={24} />
        <Skeleton width="100%" height={250} borderRadius={16} />
        <Skeleton width="100%" height={250} borderRadius={16} />
      </View>
    );
  }
  return (
    <View style={{ padding: 20, gap: 16 }}>
      <Skeleton width="100%" height={80} borderRadius={16} />
      <Skeleton width="100%" height={80} borderRadius={16} />
      <Skeleton width="100%" height={80} borderRadius={16} />
    </View>
  );
}

export function MiniStat({ label, value }) {
  return (
    <View style={styles.miniStat}>
      <Text style={styles.miniStatValue}>{value}</Text>
      <Text style={styles.miniStatLabel}>{label}</Text>
    </View>
  );
}

export function StatCard({ label, value }) {
  return (
    <View style={styles.statCard}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

export function YallaLogo({ size = 48 }) {
  return <Image source={YALLA_LOGO} style={{ width: size, height: size, borderRadius: size / 2 }} />;
}
