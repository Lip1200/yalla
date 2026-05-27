import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable as RNPressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text as RNText,
  TextInput,
  View,
  Image,
  Animated,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { useFonts, Outfit_400Regular, Outfit_600SemiBold, Outfit_700Bold } from '@expo-google-fonts/outfit';
import { Inter_400Regular, Inter_500Medium } from '@expo-google-fonts/inter';
import {
  CalendarPlus,
  Camera,
  ChefHat,
  Heart,
  Home,
  MessageCircle,
  Plus,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Target,
  Trophy,
  UserPlus,
  Users,
  X,
} from "lucide-react-native";
import * as ImagePicker from "expo-image-picker";
import * as Linking from "expo-linking";

import LoginScreen from "./components/LoginScreen";
import OnboardingScreen from "./components/OnboardingScreen";
import PedometerCard from "./components/PedometerCard";
import SetupAccountScreen from "./components/SetupAccountScreen";
import { apiDeleteVerb, getActiveAccessToken, setUnauthorizedHandler } from "./services/api";
import {
  bootstrapSession,
  clearSession,
  logoutPatient,
  refreshSession,
} from "./services/auth";

import BadgesSection from "./components/BadgesSection";
import GroupGauge from "./components/GroupGauge";
import { styles } from "./styles";

const YALLA_LOGO = require("./assets/yalla-logo.png");
const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://192.168.1.18:8001";
const PATIENT_ID = 101;
const EXPERT_PATIENT_ID = 102;

export default function App() {
  const [fontsLoaded] = useFonts({
    Outfit_400Regular,
    Outfit_600SemiBold,
    Outfit_700Bold,
    Inter_400Regular,
    Inter_500Medium,
  });

  const [activePatientId, setActivePatientId] = useState(null);
  const [activeTab, setActiveTab] = useState("home");
  // Account setup flow (#37): set when the app is opened via a
  // `?token=...` invitation URL. Renders SetupAccountScreen instead
  // of the main shell until the user finishes or cancels.
  const [setupToken, setSetupToken] = useState(null);
  // #28 — session bootstrap state
  const [session, setSession] = useState(null);
  const [authBootstrapping, setAuthBootstrapping] = useState(true);
  const [serviceView, setServiceView] = useState("messages");
  const [profile, setProfile] = useState(null);
  const [feed, setFeed] = useState([]);
  const [groups, setGroups] = useState([]);
  const [isGroupFormVisible, setIsGroupFormVisible] = useState(false);
  const [newGroupName, setNewGroupName] = useState("");
  const [newGroupDescription, setNewGroupDescription] = useState("");
  const [newGroupCategory, setNewGroupCategory] = useState("general");
  const [challengeGroupTarget, setChallengeGroupTarget] = useState(null);
  const [microChallengeTitle, setMicroChallengeTitle] = useState("");
  const [microChallengeDesc, setMicroChallengeDesc] = useState("");
  const [progression, setProgression] = useState(null);
  const [availableChallenges, setAvailableChallenges] = useState([]);
  const [restaurants, setRestaurants] = useState([]);
  const [friendSuggestions, setFriendSuggestions] = useState([]);
  const [restaurantSearchLoading, setRestaurantSearchLoading] = useState(false);
  const [restaurantSearchError, setRestaurantSearchError] = useState("");
  const [messages, setMessages] = useState([]);
  const [messageThreads, setMessageThreads] = useState({});
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [messageDraft, setMessageDraft] = useState("");
  const [settings, setSettings] = useState(null);
  const [accessSettings, setAccessSettings] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [postContent, setPostContent] = useState("");
  const [postType, setPostType] = useState("post");
  const [postImageUri, setPostImageUri] = useState(null);
  const [postImageBase64, setPostImageBase64] = useState(null);
  const [likedPosts, setLikedPosts] = useState(new Set());
  const [commentInputs, setCommentInputs] = useState({});
  const [commentsByPost, setCommentsByPost] = useState({});
  const [joinedChallengeIds, setJoinedChallengeIds] = useState(new Set());
  const [friendIds, setFriendIds] = useState(new Set());
  const [friendsList, setFriendsList] = useState([]);
  const [pendingSentIds, setPendingSentIds] = useState(new Set());
  const [sentRequests, setSentRequests] = useState([]);
  const [friendRequests, setFriendRequests] = useState([]);
  const [isNewConvModalVisible, setIsNewConvModalVisible] = useState(false);
  const [sessionTitle, setSessionTitle] = useState("");
  const [sessionKind, setSessionKind] = useState("group");
  const [sessionDate, setSessionDate] = useState("");
  const [sessionCapacity, setSessionCapacity] = useState("10");
  const [sessionNotes, setSessionNotes] = useState("");
  const [joinedSessions, setJoinedSessions] = useState(new Set());

  const isExpert = profile?.role === "expert_patient";
  const tabs = useMemo(() => {
    const baseTabs = [
      { id: "home", label: "Accueil", icon: Home },
      { id: "progress", label: "Défis", icon: Target },
      { id: "community", label: "Communauté", icon: Users },
      { id: "services", label: "Services", icon: Settings },
    ];

    baseTabs.splice(3, 0, { id: "sessions", label: "Séances", icon: CalendarPlus });

    return baseTabs;
  }, [isExpert]);

  // #37 — detect a `?token=...` URL on app launch (deep link or pasted
  // by the user via the Setup screen's input). Both the initial URL and
  // any subsequent URL event (foregrounded from a notification, etc.)
  // are inspected.
  useEffect(() => {
    let cancelled = false;
    function extractToken(url) {
      if (!url) return null;
      try {
        const parsed = Linking.parse(url);
        const token = parsed?.queryParams?.token;
        return typeof token === "string" && token.length > 0 ? token : null;
      } catch {
        return null;
      }
    }
    (async () => {
      const initial = await Linking.getInitialURL();
      const tok = extractToken(initial);
      if (!cancelled && tok) setSetupToken(tok);
    })();
    const sub = Linking.addEventListener("url", ({ url }) => {
      const tok = extractToken(url);
      if (tok) setSetupToken(tok);
    });
    return () => {
      cancelled = true;
      sub?.remove?.();
    };
  }, []);

  // #28 — bootstrap session + install refresh-on-401 handler.
  useEffect(() => {
    let cancelled = false;
    setUnauthorizedHandler(async () => {
      const refreshed = await refreshSession();
      if (!refreshed) {
        if (!cancelled) {
          setSession(null);
          setActivePatientId(null);
        }
        return null;
      }
      if (!cancelled) setSession(refreshed);
      return refreshed.access_token;
    });
    (async () => {
      const existing = await bootstrapSession();
      if (cancelled) return;
      setSession(existing);
      setAuthBootstrapping(false);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // #28 — when authenticated, resolve the integer profile.id via
  // GET /api/users/me so the rest of the app can stop using the
  // hardcoded PATIENT_ID constant.
  useEffect(() => {
    if (!session) {
      setActivePatientId(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const me = await apiGet("/api/users/me");
        if (!cancelled && me?.id) setActivePatientId(me.id);
      } catch (error) {
        // Two failure modes:
        //  - session expired (refresh already cleared session via the
        //    unauthorized handler → next render shows the login screen)
        //  - 404 "Aucun profil rattaché" → fresh signup that never got a
        //    profile row. Force a clean logout so the user re-signs in
        //    rather than being silently logged into Karim's account.
        if (!cancelled) {
          await clearSession();
          setSession(null);
          setActivePatientId(null);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [session]);

  useEffect(() => {
    if (activePatientId) loadApp();
  }, [activePatientId]);

  async function handleLogout() {
    await logoutPatient();
    setSession(null);
    setActivePatientId(null);
    setProfile(null);
    setFeed([]);
    setProgression(null);
    setActiveTab("home");
  }

  async function loadApp() {
    setLoading(true);

    try {
      const paths = [
        `/api/patients/${activePatientId}/profile`,
        `/api/patients/${activePatientId}/feed`,
        `/api/patients/${activePatientId}/progression`,
        "/api/restaurants/recommendations",
        `/api/patients/${activePatientId}/messages`,
        `/api/patients/${activePatientId}/settings`,
        "/api/social/groups",
        "/api/challenges/",
        `/api/social/suggestions/${activePatientId}`,
        `/api/social/friends/${activePatientId}`,
        `/api/social/friends/${activePatientId}/requests`,
        `/api/social/friends/${activePatientId}/sent`,
      ];
      const results = await Promise.allSettled(paths.map((p) => apiGet(p)));
      const firstReject = results.findIndex((r) => r.status === "rejected");
      if (firstReject !== -1) {
        const r = results[firstReject];
        console.warn(`[loadApp] ${paths[firstReject]} failed:`, r.reason?.message);
        throw r.reason;
      }
      const [profileData, feedData, progressionData, restaurantData, messageData, settingsData, groupsData, challengesData, suggestionsData, friendsData, requestsData, sentData] = results.map((r) => r.value);

      setProfile(profileData);
      setFeed(feedData);
      setGroups(groupsData);
      setProgression(progressionData);
      setAvailableChallenges(challengesData);
      setFriendSuggestions(suggestionsData);
      setRestaurants(restaurantData);
      setFriendsList(friendsData ?? []);
      setFriendRequests(requestsData ?? []);
      setSentRequests(sentData ?? []);
      setPendingSentIds(new Set((sentData ?? []).map((s) => s.id)));
      setFriendIds(new Set((friendsData ?? []).map((f) => f.id)));
      setMessages(messageData);
      setSelectedConversationId(messageData[0]?.id ?? null);
      setMessageThreads(buildThreads(messageData));
      setSettings(settingsData);
      setAccessSettings({
        share_activity: settingsData.share_activity,
        share_challenges: settingsData.share_challenges,
        share_restaurants: settingsData.share_restaurants,
        share_posts: true,
        share_messages_with_expert: true,
      });

      setSessions(await apiGet(`/api/patients/${activePatientId}/sessions`));
    } catch (error) {
      console.warn("[loadApp] failed:", error?.message, error);
      Alert.alert("Erreur", error?.message ?? "Échec du chargement");
    } finally {
      setLoading(false);
    }
  }

  const searchRestaurants = useCallback(async (query) => {
    const trimmedQuery = query.trim();
    setRestaurantSearchLoading(true);
    setRestaurantSearchError("");

    try {
      const params = trimmedQuery
        ? `?q=${encodeURIComponent(trimmedQuery)}&radius_m=5000&limit=30`
        : "?radius_m=2500&limit=20";
      const restaurantData = await apiGet(`/api/restaurants/recommendations${params}`);
      setRestaurants(mergeRestaurants(restaurantData));
    } catch (error) {
      setRestaurantSearchError("Recherche impossible pour le moment.");
    } finally {
      setRestaurantSearchLoading(false);
    }
  }, []);

  async function createPost() {
    if (!postContent.trim() && !postImageBase64) {
      Alert.alert("Publication vide", "Écris quelque chose ou ajoute une photo avant de publier.");
      return;
    }

    try {
      const payload = {
        type: postType,
        content: postContent.trim() || "📸 Photo partagée",
        achievement_label: postType === "achievement" ? "Nouvelle réussite" : null,
      };
      if (postImageBase64) {
        payload.image_base64 = `data:image/jpeg;base64,${postImageBase64}`;
      }

      const createdPost = await apiPost(`/api/patients/${activePatientId}/feed`, payload);
      setFeed([createdPost, ...feed]);
      setPostContent("");
      setPostType("post");
      setPostImageUri(null);
      setPostImageBase64(null);
      setActiveTab("community");
    } catch (error) {
      Alert.alert("Erreur", error.message);
    }
  }

  async function createGroup() {
    if (!newGroupName.trim()) {
      Alert.alert("Nom requis", "Veuillez donner un nom à votre groupe.");
      return;
    }
    try {
      const payload = {
        name: newGroupName.trim(),
        description: newGroupDescription.trim(),
        category: newGroupCategory,
        creator_id: activePatientId,
      };
      const createdGroup = await apiPost("/api/social/groups", payload);
      setGroups([createdGroup, ...groups]);
      setIsGroupFormVisible(false);
      setNewGroupName("");
      setNewGroupDescription("");
      setNewGroupCategory("general");
    } catch (error) {
      Alert.alert("Erreur", error.message);
    }
  }

  function launchMicroChallenge() {
    if (!microChallengeTitle.trim()) {
      Alert.alert("Titre requis", "Veuillez donner un titre à ce défi.");
      return;
    }
    Alert.alert("Défi lancé !", `Le défi "${microChallengeTitle}" a bien été envoyé au groupe.`);
    setChallengeGroupTarget(null);
    setMicroChallengeTitle("");
    setMicroChallengeDesc("");
  }

  async function pickImage() {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      quality: 0.5,
      base64: true,
    });

    if (!result.canceled) {
      setPostImageUri(result.assets[0].uri);
      setPostImageBase64(result.assets[0].base64);
    }
  }

  function clearImage() {
    setPostImageUri(null);
    setPostImageBase64(null);
  }

  async function createSession() {
    if (!sessionTitle.trim() || !sessionDate.trim() || !sessionCapacity.trim()) {
      Alert.alert("Champs manquants", "Ajoutez un titre, une date et une capacité.");
      return;
    }

    try {
      const parsedCapacity = parseInt(sessionCapacity, 10) || 10;
      const scheduledFor = new Date(sessionDate).toISOString();

      const createdSession = await apiPost(`/api/patients/${activePatientId}/sessions`, {
        title: sessionTitle.trim(),
        kind: sessionKind,
        scheduled_for: scheduledFor,
        capacity: parsedCapacity,
        notes: sessionNotes.trim(),
      });
      setSessions([createdSession, ...sessions]);
      setSessionTitle("");
      setSessionDate("");
      setSessionCapacity("10");
      setSessionNotes("");
      setSessionKind("group");
      Alert.alert("Succès", "Séance organisée avec succès !");
    } catch (error) {
      Alert.alert("Erreur", "Veuillez entrer une date valide (ex: 2026-06-15T14:00:00).");
    }
  }

  async function joinSession(sessionId) {
    if (joinedSessions.has(sessionId)) return;
    try {
      await apiPost(`/api/patients/${activePatientId}/sessions/${sessionId}/join`, {});
      setJoinedSessions(new Set(joinedSessions).add(sessionId));
      
      setSessions(
        sessions.map((s) => {
          if (s.id === sessionId) {
            return { ...s, enrolled_count: s.enrolled_count + 1 };
          }
          return s;
        })
      );
      Alert.alert("Succès", "Vous avez rejoint la séance !");
    } catch (error) {
      Alert.alert("Erreur", "Impossible de rejoindre la séance.");
    }
  }

  async function updatePrivacy(isPrivate) {
    try {
      const nextSettings = await apiPatch(`/api/patients/${activePatientId}/settings/privacy`, {
        privacy_level: isPrivate ? "Données privées" : "Partage sélectif",
      });
      setSettings(nextSettings);
      setProfile(nextSettings.profile);
      setAccessSettings((current) => ({
        ...current,
        share_activity: !isPrivate,
        share_challenges: !isPrivate,
        share_restaurants: !isPrivate,
      }));
    } catch (error) {
      Alert.alert("Erreur", error.message);
    }
  }

  async function toggleAccess(key) {
    // Persisted backend flags: share_activity, share_challenges, share_restaurants.
    // The patient-app also exposes share_posts / share_messages_with_expert as
    // UI-only switches for now (no backend column yet); those stay local.
    const persistedKeys = new Set(["share_activity", "share_challenges", "share_restaurants"]);
    const nextValue = !accessSettings?.[key];
    setAccessSettings((current) => ({ ...current, [key]: nextValue }));
    if (!persistedKeys.has(key)) return;
    try {
      const updated = await apiPatch(`/api/patients/${activePatientId}/settings/access`, {
        [key]: nextValue,
      });
      // Reconcile with the server's authoritative state.
      setAccessSettings((current) => ({
        ...current,
        share_activity: updated.share_activity,
        share_challenges: updated.share_challenges,
        share_restaurants: updated.share_restaurants,
      }));
    } catch (error) {
      // Roll back the optimistic flip so the UI stays in sync with the
      // backend.
      setAccessSettings((current) => ({ ...current, [key]: !nextValue }));
      Alert.alert("Préférence non enregistrée", error.message);
    }
  }

  function toggleLike(postId) {
    setLikedPosts((current) => {
      const next = new Set(current);
      if (next.has(postId)) {
        next.delete(postId);
      } else {
        next.add(postId);
      }
      return next;
    });
  }

  function addComment(postId) {
    const text = commentInputs[postId]?.trim();
    if (!text) {
      return;
    }

    setCommentsByPost((current) => ({
      ...current,
      [postId]: [...(current[postId] ?? []), { id: Date.now(), author: profile.full_name, text }],
    }));
    setCommentInputs((current) => ({ ...current, [postId]: "" }));
  }

  async function joinChallenge(challenge) {
    try {
      await apiPost("/api/challenges/assignments", {
        patient_id: activePatientId,
        challenge_id: challenge.id,
      });
      setJoinedChallengeIds((current) => new Set(current).add(challenge.id));
      const fresh = await apiGet(`/api/patients/${activePatientId}/progression`);
      setProgression(fresh);
    } catch (error) {
      Alert.alert("Défi non rejoint", error.message);
    }
  }

  async function joinGroup(groupId) {
    try {
      const updated = await apiPost(`/api/social/groups/${groupId}/join`, {
        user_id: activePatientId,
      });
      setGroups((current) =>
        current.map((g) => (g.id === groupId ? { ...g, ...updated } : g)),
      );
    } catch (error) {
      Alert.alert("Groupe non rejoint", error.message);
    }
  }

  async function addFriend(friendId) {
    try {
      const newFriend = await apiPost(`/api/social/friends/${activePatientId}`, { friend_id: friendId });
      if (newFriend.status === "accepted") {
        setFriendIds((current) => new Set(current).add(friendId));
        setFriendsList((current) => (current.some((f) => f.id === friendId) ? current : [newFriend, ...current]));
      } else {
        // 'pending' — the receiver still has to accept. Mark locally so the
        // 'Ajouter' button shows 'Demandé' and add to the sentRequests list.
        setPendingSentIds((current) => new Set(current).add(friendId));
        setSentRequests((current) => (current.some((s) => s.id === friendId) ? current : [newFriend, ...current]));
        Alert.alert("Demande envoyée", `${newFriend.name} doit accepter avant que la connexion soit active.`);
      }
    } catch (error) {
      Alert.alert("Demande échouée", error.message);
    }
  }

  async function acceptFriendRequest(requesterId) {
    try {
      const newFriend = await apiPost(
        `/api/social/friends/${activePatientId}/requests/${requesterId}/accept`,
        {},
      );
      setFriendIds((current) => new Set(current).add(requesterId));
      setFriendsList((current) => (current.some((f) => f.id === requesterId) ? current : [newFriend, ...current]));
      setFriendRequests((current) => current.filter((r) => r.requester_id !== requesterId));
    } catch (error) {
      Alert.alert("Acceptation échouée", error.message);
    }
  }

  async function cancelSentRequest(friendId) {
    try {
      await apiDeleteVerb(`/api/social/friends/${activePatientId}/${friendId}`);
    } catch (error) {
      Alert.alert("Annulation échouée", error.message);
      return;
    }
    setPendingSentIds((current) => {
      const next = new Set(current);
      next.delete(friendId);
      return next;
    });
    setSentRequests((current) => current.filter((s) => s.id !== friendId));
  }

  async function rejectFriendRequest(requesterId) {
    try {
      await apiPost(`/api/social/friends/${activePatientId}/requests/${requesterId}/reject`, {});
    } catch (error) {
      Alert.alert("Rejet échoué", error.message);
      return;
    }
    setFriendRequests((current) => current.filter((r) => r.requester_id !== requesterId));
  }

  async function startConversationWith(friendId) {
    try {
      const conv = await apiPost(`/api/patients/${activePatientId}/messages/start`, { friend_id: friendId });
      setMessages((current) => {
        if (current.some((c) => c.id === conv.id)) return current;
        return [conv, ...current];
      });
      setSelectedConversationId(conv.id);
      setIsNewConvModalVisible(false);
      setActiveTab("services");
      setServiceView("messages");
    } catch (error) {
      Alert.alert("Conversation non démarrée", error.message);
    }
  }

  function sendMessage() {
    const text = messageDraft.trim();
    if (!text || !selectedConversationId) {
      return;
    }

    setMessageThreads((current) => ({
      ...current,
      [selectedConversationId]: [
        ...(current[selectedConversationId] ?? []),
        { id: Date.now(), fromMe: true, text, time: "Maintenant" },
      ],
    }));
    setMessages((current) =>
      current.map((conversation) =>
        conversation.id === selectedConversationId
          ? { ...conversation, last_message: text, unread_count: 0, updated_at: new Date().toISOString() }
          : conversation,
      ),
    );
    setMessageDraft("");
  }

  if (!fontsLoaded) {
    return (
      <SafeAreaProvider>
        <SafeAreaView style={styles.centered}>
          <YallaLogo size={72} />
          <ActivityIndicator color="#0f766e" size="large" />
          <RNText style={styles.loadingText}>Yalla</RNText>
        </SafeAreaView>
      </SafeAreaProvider>
    );
  }

  // #37 — Patient opened the app via an invitation link → bypass the
  // normal shell and walk them through password setup.
  if (setupToken) {
    return (
      <SafeAreaProvider>
        <SafeAreaView style={styles.screen}>
          <StatusBar style="dark" />
          <SetupAccountScreen
            initialToken={setupToken}
            onDone={() => setSetupToken(null)}
          />
        </SafeAreaView>
      </SafeAreaProvider>
    );
  }

  // #28 — auth gate: still bootstrapping?
  if (authBootstrapping) {
    return (
      <SafeAreaProvider>
        <SafeAreaView style={styles.centered}>
          <YallaLogo size={72} />
          <ActivityIndicator color="#0f766e" size="large" />
        </SafeAreaView>
      </SafeAreaProvider>
    );
  }

  // #28 — not authenticated → show login/signup.
  if (!session) {
    return (
      <SafeAreaProvider>
        <SafeAreaView style={styles.screen}>
          <StatusBar style="dark" />
          <LoginScreen onAuthenticated={(s) => setSession(s)} />
        </SafeAreaView>
      </SafeAreaProvider>
    );
  }

  const isLoadingApp = loading || !profile || !progression || !settings || !accessSettings;

  // #8 — Onboarding gate. PatientProfile exposes the DB column
  // `primary_goal` as `main_goal`. A fresh signup auto-provisions the
  // profiles row with main_goal='' (cf. _ensure_profile_for_auth_user),
  // which is our trigger to render the welcome flow instead of the main
  // shell. Once submitted, the PATCH updates primary_goal and the
  // patient profile refetch reflects it as `main_goal`, so this check
  // returns false on the next render.
  const isFreshProfile =
    !!profile &&
    profile.role === "patient" &&
    !(profile.main_goal || "").trim();

  if (isFreshProfile) {
    return (
      <SafeAreaProvider>
        <SafeAreaView style={styles.screen}>
          <StatusBar style="dark" />
          <OnboardingScreen
            profileId={profile.id}
            profileName={profile.full_name}
            onComplete={async () => {
              // Refetch the patient profile shape so the rest of the app
              // sees the new age/primary_goal/privacy_level immediately
              // (PATCH /api/users returns the legacy Profile schema; we
              // want PatientProfile here).
              try {
                const fresh = await apiGet(`/api/patients/${activePatientId}/profile`);
                setProfile(fresh);
              } catch {}
            }}
          />
        </SafeAreaView>
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.screen}>
        <StatusBar style="dark" />
        <View style={styles.header}>
          <Pressable
            onPress={() => setActiveTab("profile")}
            style={styles.headerIdentity}
            accessibilityRole="button"
            accessibilityLabel="Ouvrir mon profil"
          >
            <YallaLogo size={48} />
            <View>
              <Text style={styles.greeting}>Bonjour</Text>
              {profile ? (
                <Text style={styles.userName}>{profile.full_name}</Text>
              ) : (
                <Skeleton width={150} height={28} style={{ marginTop: 4 }} />
              )}
            </View>
          </Pressable>
          <View style={styles.roleSwitch}>
            <Text style={styles.roleSwitchText}>{isExpert ? "Expert" : "Patient"}</Text>
          </View>
        </View>

        <View style={styles.content}>
          {isLoadingApp ? <ScreenSkeleton activeTab={activeTab} /> : renderTab()}
        </View>

        <View style={styles.tabBar}>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <Pressable key={tab.id} onPress={() => setActiveTab(tab.id)} style={styles.tabButton}>
                <Icon size={21} color={isActive ? "#0f766e" : "#64748b"} />
                <Text style={[styles.tabLabel, isActive && styles.tabLabelActive]}>{tab.label}</Text>
              </Pressable>
            );
          })}
        </View>
      </SafeAreaView>
    </SafeAreaProvider>
  );

  function renderTab() {
    if (activeTab === "profile") {
      return (
        <ProfileScreen
          profile={profile}
          progression={progression}
          patientId={activePatientId}
          isExpert={isExpert}
          onClose={() => setActiveTab("home")}
          onLogout={handleLogout}
        />
      );
    }
    if (activeTab === "home") {
      return <HomeScreen progression={progression} profile={profile} setActiveTab={setActiveTab} />;
    }
    if (activeTab === "progress") {
      return (
        <ProgressScreen
          joinedChallengeIds={joinedChallengeIds}
          onJoinChallenge={joinChallenge}
          progression={progression}
          patientId={activePatientId}
          availableChallenges={availableChallenges}
        />
      );
    }
    if (activeTab === "community") {
      return (
        <CommunityScreen
          groups={groups}
          isGroupFormVisible={isGroupFormVisible}
          newGroupName={newGroupName}
          newGroupDescription={newGroupDescription}
          newGroupCategory={newGroupCategory}
          onCreateGroup={createGroup}
          setIsGroupFormVisible={setIsGroupFormVisible}
          setNewGroupName={setNewGroupName}
          setNewGroupDescription={setNewGroupDescription}
          setNewGroupCategory={setNewGroupCategory}
          challengeGroupTarget={challengeGroupTarget}
          microChallengeTitle={microChallengeTitle}
          microChallengeDesc={microChallengeDesc}
          setChallengeGroupTarget={setChallengeGroupTarget}
          setMicroChallengeTitle={setMicroChallengeTitle}
          setMicroChallengeDesc={setMicroChallengeDesc}
          onLaunchMicroChallenge={launchMicroChallenge}
          commentInputs={commentInputs}
          commentsByPost={commentsByPost}
          feed={feed}
          friendIds={friendIds}
          friendRequests={friendRequests}
          friendSuggestions={friendSuggestions}
          isExpert={isExpert}
          likedPosts={likedPosts}
          onAcceptFriend={acceptFriendRequest}
          onAddComment={addComment}
          onAddFriend={addFriend}
          onCancelSentRequest={cancelSentRequest}
          onCreatePost={createPost}
          onJoinGroup={joinGroup}
          onRejectFriend={rejectFriendRequest}
          onToggleLike={toggleLike}
          pendingSentIds={pendingSentIds}
          sentRequests={sentRequests}
          postContent={postContent}
          postType={postType}
          setCommentInputs={setCommentInputs}
          setPostContent={setPostContent}
          setPostType={setPostType}
          postImageUri={postImageUri}
          onPickImage={pickImage}
          onClearImage={clearImage}
        />
      );
    }
    if (activeTab === "services") {
      return (
        <ServicesScreen
          accessSettings={accessSettings}
          friendsList={friendsList}
          isNewConvModalVisible={isNewConvModalVisible}
          messageDraft={messageDraft}
          messageThreads={messageThreads}
          messages={messages}
          onSendMessage={sendMessage}
          onStartConversation={startConversationWith}
          onToggleAccess={toggleAccess}
          onUpdatePrivacy={updatePrivacy}
          restaurants={restaurants}
          restaurantSearchError={restaurantSearchError}
          restaurantSearchLoading={restaurantSearchLoading}
          onSearchRestaurants={searchRestaurants}
          selectedConversationId={selectedConversationId}
          serviceView={serviceView}
          setIsNewConvModalVisible={setIsNewConvModalVisible}
          setMessageDraft={setMessageDraft}
          setSelectedConversationId={setSelectedConversationId}
          setServiceView={setServiceView}
          settings={settings}
          onLogout={handleLogout}
        />
      );
    }
    return (
      <SessionsScreen
        sessions={sessions}
        sessionTitle={sessionTitle}
        setSessionTitle={setSessionTitle}
        sessionKind={sessionKind}
        setSessionKind={setSessionKind}
        sessionDate={sessionDate}
        setSessionDate={setSessionDate}
        sessionCapacity={sessionCapacity}
        setSessionCapacity={setSessionCapacity}
        sessionNotes={sessionNotes}
        setSessionNotes={setSessionNotes}
        joinedSessions={joinedSessions}
        onCreateSession={createSession}
        onJoinSession={joinSession}
        isExpert={isExpert}
      />
    );
  }
}

function HomeScreen({ progression, profile, setActiveTab }) {
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

function ProfileScreen({ profile, progression, patientId, isExpert, onClose, onLogout }) {
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

      <Pressable onPress={onClose} style={[styles.secondaryButton, {marginTop: 8}]}>
        <Text style={styles.secondaryButtonText}>Retour à l'accueil</Text>
      </Pressable>
      <Pressable onPress={onLogout} style={[styles.secondaryButton, {marginTop: 8, borderColor: "#fecaca"}]}>
        <Text style={[styles.secondaryButtonText, {color: "#b91c1c"}]}>Se déconnecter</Text>
      </Pressable>
    </ScrollView>
  );
}


function ProgressScreen({ joinedChallengeIds, onJoinChallenge, progression, patientId, availableChallenges }) {
  // progression.active_challenges is the source of truth (refreshed from DB after
  // joinChallenge). joinedChallengeIds is kept locally as a fast filter for the
  // "Rejoindre un défi" carousel between click and refresh.
  const availableSuggestions = availableChallenges.filter((challenge) => !joinedChallengeIds.has(challenge.id));
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
      <Text style={styles.cardFooter}>{progress}% {dueLabel}</Text>
    </View>
  );
}

function CommunityScreen({
  isExpert,
  groups,
  isGroupFormVisible,
  newGroupName,
  newGroupDescription,
  newGroupCategory,
  challengeGroupTarget,
  microChallengeTitle,
  microChallengeDesc,
  setChallengeGroupTarget,
  setMicroChallengeTitle,
  setMicroChallengeDesc,
  onLaunchMicroChallenge,
  onCreateGroup,
  setIsGroupFormVisible,
  setNewGroupName,
  setNewGroupDescription,
  setNewGroupCategory,
  commentInputs,
  commentsByPost,
  feed,
  friendIds,
  friendRequests,
  friendSuggestions,
  likedPosts,
  onAcceptFriend,
  onCancelSentRequest,
  onRejectFriend,
  pendingSentIds,
  sentRequests,
  onAddComment,
  onAddFriend,
  onCreatePost,
  onJoinGroup,
  onToggleLike,
  postContent,
  postType,
  setCommentInputs,
  setPostContent,
  setPostType,
  postImageUri,
  onPickImage,
  onClearImage,
}) {
  return (
    <FlatList
      ListHeaderComponent={
        <View style={styles.stack}>
          <Composer
            onCreatePost={onCreatePost}
            postContent={postContent}
            postType={postType}
            setPostContent={setPostContent}
            setPostType={setPostType}
            postImageUri={postImageUri}
            onPickImage={onPickImage}
            onClearImage={onClearImage}
          />
          {friendRequests.length > 0 ? (
            <>
              <Text style={styles.sectionTitle}>Demandes reçues</Text>
              {friendRequests.map((req) => (
                <View key={req.requester_id} style={[styles.card, {marginBottom: 8}]}>
                  <Text style={styles.cardTitle}>{req.requester_name}</Text>
                  {req.primary_goal ? (
                    <Text style={styles.cardMeta}>{req.primary_goal}</Text>
                  ) : null}
                  <View style={{flexDirection: "row", gap: 8, marginTop: 10}}>
                    <Pressable
                      onPress={() => onAcceptFriend(req.requester_id)}
                      style={[styles.primaryButton, {flex: 1}]}
                    >
                      <Text style={styles.primaryButtonText}>Accepter</Text>
                    </Pressable>
                    <Pressable
                      onPress={() => onRejectFriend(req.requester_id)}
                      style={[styles.secondaryButton, {flex: 1}]}
                    >
                      <Text style={styles.secondaryButtonText}>Refuser</Text>
                    </Pressable>
                  </View>
                </View>
              ))}
            </>
          ) : null}

          {sentRequests.length > 0 ? (
            <>
              <Text style={styles.sectionTitle}>Demandes envoyées</Text>
              {sentRequests.map((req) => (
                <View key={req.id} style={[styles.card, {marginBottom: 8}]}>
                  <Text style={styles.cardTitle}>{req.name}</Text>
                  {req.primary_goal ? (
                    <Text style={styles.cardMeta}>{req.primary_goal}</Text>
                  ) : null}
                  <Text style={[styles.cardMeta, {fontStyle: "italic", marginTop: 4}]}>
                    En attente d'acceptation
                  </Text>
                  <Pressable
                    onPress={() => onCancelSentRequest(req.id)}
                    style={[styles.secondaryButton, {marginTop: 10}]}
                  >
                    <Text style={styles.secondaryButtonText}>Annuler la demande</Text>
                  </Pressable>
                </View>
              ))}
            </>
          ) : null}

          <Text style={styles.sectionTitle}>Ajouter des amis</Text>
          {friendSuggestions.length === 0 ? (
            <Text style={styles.cardMeta}>Aucune suggestion pour le moment.</Text>
          ) : (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.friendRail}>
              {friendSuggestions.map((friend) => {
                const isFriend = friendIds.has(friend.id);
                const isPending = pendingSentIds.has(friend.id);
                const label = isFriend ? "Ami" : isPending ? "Demandé" : "Ajouter";
                return (
                  <View key={friend.id} style={styles.friendCard}>
                    <Text style={styles.cardTitle}>{friend.name}</Text>
                    <Text style={styles.cardMeta}>{friend.detail}</Text>
                    <Pressable
                      onPress={() => onAddFriend(friend.id)}
                      style={styles.secondaryButton}
                      disabled={isFriend || isPending}
                    >
                      <UserPlus size={16} color="#0f766e" />
                      <Text style={styles.secondaryButtonText}>{label}</Text>
                    </Pressable>
                  </View>
                );
              })}
            </ScrollView>
          )}

          <Text style={styles.sectionTitle}>Groupes de soutien</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.friendRail}>
            {isExpert && (
              <View style={[styles.friendCard, styles.groupCard]}>
                <Pressable onPress={() => setIsGroupFormVisible(true)} style={[styles.secondaryButton, {flex: 1, justifyContent: 'center', backgroundColor: '#f8fafc', borderColor: '#cbd5e1', borderWidth: 1, borderStyle: 'dashed'}]}>
                  <Plus size={24} color="#0f766e" />
                  <Text style={[styles.secondaryButtonText, {marginTop: 8, fontSize: 13, color: '#475569'}]}>Créer un groupe</Text>
                </Pressable>
              </View>
            )}
            {groups.map((group) => (
              <View key={group.id} style={[styles.friendCard, styles.groupCard]}>
                <Text style={styles.cardTitle} numberOfLines={1}>{group.name}</Text>
                <Text style={styles.cardMeta}>{group.category === "walking" ? "Marche" : group.category === "cooking" ? "Cuisine" : group.category === "support" ? "Soutien" : "Général"} · {group.member_count} membre(s)</Text>
                <Text style={styles.cardBody} numberOfLines={3}>{group.description}</Text>
                <View style={{flex: 1}} />
                <Pressable onPress={() => onJoinGroup(group.id)} style={[styles.primaryButton, {marginTop: 10}]}>
                  <Text style={styles.primaryButtonText}>Rejoindre</Text>
                </Pressable>
                {isExpert && (
                  <Pressable onPress={() => setChallengeGroupTarget(group.id)} style={[styles.secondaryButton, {marginTop: 8}]}>
                    <Target size={16} color="#0f766e" />
                    <Text style={styles.secondaryButtonText}>Lancer un défi</Text>
                  </Pressable>
                )}
              </View>
            ))}
          </ScrollView>

          {challengeGroupTarget && (
            <View style={styles.card}>
              <View style={[styles.cardHeader, {marginBottom: 16}]}>
                <View style={{flexDirection: 'row', alignItems: 'center'}}>
                  <Target size={20} color="#0f766e" style={{marginRight: 8}} />
                  <Text style={styles.cardTitle}>Lancer un défi au groupe</Text>
                </View>
                <Pressable onPress={() => setChallengeGroupTarget(null)}>
                  <X size={20} color="#64748b" />
                </Pressable>
              </View>
              <TextInput
                onChangeText={setMicroChallengeTitle}
                placeholder="Titre du défi (ex: 10 min de marche)"
                placeholderTextColor="#94a3b8"
                style={styles.input}
                value={microChallengeTitle}
              />
              <TextInput
                onChangeText={setMicroChallengeDesc}
                placeholder="Description et règles du défi"
                placeholderTextColor="#94a3b8"
                style={[styles.input, {marginTop: 12}]}
                value={microChallengeDesc}
              />
              <Pressable onPress={onLaunchMicroChallenge} style={[styles.primaryButton, {marginTop: 16, backgroundColor: '#0f766e'}]}>
                <Text style={styles.primaryButtonText}>Envoyer le défi</Text>
              </Pressable>
            </View>
          )}

          {isGroupFormVisible && (
            <View style={styles.card}>
              <View style={[styles.cardHeader, {marginBottom: 16}]}>
                <Text style={styles.cardTitle}>Nouveau groupe</Text>
                <Pressable onPress={() => setIsGroupFormVisible(false)}>
                  <X size={20} color="#64748b" />
                </Pressable>
              </View>
              <TextInput
                onChangeText={setNewGroupName}
                placeholder="Nom du groupe"
                placeholderTextColor="#94a3b8"
                style={styles.input}
                value={newGroupName}
              />
              <TextInput
                onChangeText={setNewGroupDescription}
                placeholder="Description"
                placeholderTextColor="#94a3b8"
                style={[styles.input, {marginTop: 12}]}
                value={newGroupDescription}
              />
              <View style={[styles.segmented, {marginTop: 12, marginBottom: 16, backgroundColor: '#f1f5f9'}]}>
                {["general", "walking", "cooking", "support"].map((cat) => (
                  <Pressable 
                    key={cat} 
                    onPress={() => setNewGroupCategory(cat)} 
                    style={[styles.segment, newGroupCategory === cat && styles.segmentActive]}
                  >
                    <Text style={[styles.segmentText, newGroupCategory === cat && styles.segmentTextActive]}>
                      {cat === "walking" ? "Marche" : cat === "cooking" ? "Cuisine" : cat === "support" ? "Soutien" : "Général"}
                    </Text>
                  </Pressable>
                ))}
              </View>
              <Pressable onPress={onCreateGroup} style={styles.primaryButton}>
                <Text style={styles.primaryButtonText}>Créer</Text>
              </Pressable>
            </View>
          )}

          <Text style={styles.sectionTitle}>Fil d'activité</Text>
        </View>
      }
      contentContainerStyle={styles.listContent}
      data={feed}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => (
        <FeedCard
          commentInput={commentInputs[item.id] ?? ""}
          comments={commentsByPost[item.id] ?? []}
          isLiked={likedPosts.has(item.id)}
          onAddComment={() => onAddComment(item.id)}
          onChangeComment={(text) => setCommentInputs((current) => ({ ...current, [item.id]: text }))}
          onToggleLike={() => onToggleLike(item.id)}
          post={item}
        />
      )}
    />
  );
}

function Composer({ onCreatePost, postContent, postType, setPostContent, setPostType, postImageUri, onPickImage, onClearImage }) {
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Publier</Text>
      <View style={styles.segmented}>
        <Pressable onPress={() => setPostType("post")} style={[styles.segment, postType === "post" && styles.segmentActive]}>
          <Text style={[styles.segmentText, postType === "post" && styles.segmentTextActive]}>Post</Text>
        </Pressable>
        <Pressable
          onPress={() => setPostType("achievement")}
          style={[styles.segment, postType === "achievement" && styles.segmentActive]}
        >
          <Text style={[styles.segmentText, postType === "achievement" && styles.segmentTextActive]}>Réussite</Text>
        </Pressable>
      </View>
      <TextInput
        multiline
        onChangeText={setPostContent}
        placeholder="Partage un progres, une question ou une sortie..."
        placeholderTextColor="#94a3b8"
        style={styles.textArea}
        value={postContent}
      />
      {postImageUri && (
        <View style={styles.imagePreviewContainer}>
          <Image source={{ uri: postImageUri }} style={styles.imagePreview} />
          <Pressable onPress={onClearImage} style={styles.clearImageBtn}>
            <X size={16} color="#fff" />
          </Pressable>
        </View>
      )}
      <View style={styles.composerActions}>
        <Pressable onPress={onPickImage} style={styles.composerIconButton}>
          <Camera size={20} color="#0f766e" />
        </Pressable>
        <Pressable onPress={onCreatePost} style={[styles.primaryButton, { flex: 1, marginTop: 0, marginLeft: 12 }]}>
          <Text style={styles.primaryButtonText}>Publier</Text>
        </Pressable>
      </View>
    </View>
  );
}

function FeedCard({ commentInput, comments, isLiked, onAddComment, onChangeComment, onToggleLike, post }) {
  const isAchievement = post.type === "achievement";
  const likes = post.likes + (isLiked ? 1 : 0);
  const commentCount = post.comments_count + comments.length;

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View>
          <Text style={styles.cardTitle}>{post.author_name}</Text>
          <Text style={styles.cardMeta}>{post.author_role === "expert_patient" ? "Patient expert" : "Patient"}</Text>
        </View>
        {isAchievement ? <Trophy size={22} color="#d97706" /> : <Users size={22} color="#0f766e" />}
      </View>
      {post.achievement_label ? <Text style={styles.achievementLabel}>{post.achievement_label}</Text> : null}
      <Text style={styles.cardBody}>{post.content}</Text>
      {post.image_url ? <Image source={{ uri: post.image_url }} style={styles.feedImage} /> : null}
      <View style={styles.actionRow}>
        <Pressable onPress={onToggleLike} style={[styles.actionButton, isLiked && styles.actionButtonActive]}>
          <Heart size={17} color={isLiked ? "#be123c" : "#64748b"} fill={isLiked ? "#be123c" : "transparent"} />
          <Text style={[styles.actionText, isLiked && styles.actionTextActive]}>{likes}</Text>
        </Pressable>
        <View style={styles.actionButton}>
          <MessageCircle size={17} color="#64748b" />
          <Text style={styles.actionText}>{commentCount}</Text>
        </View>
      </View>
      {comments.map((comment) => (
        <View key={comment.id} style={styles.commentBubble}>
          <Text style={styles.commentAuthor}>{comment.author}</Text>
          <Text style={styles.commentText}>{comment.text}</Text>
        </View>
      ))}
      <View style={styles.commentComposer}>
        <TextInput
          onChangeText={onChangeComment}
          placeholder="Commenter..."
          placeholderTextColor="#94a3b8"
          style={styles.commentInput}
          value={commentInput}
        />
        <Pressable onPress={onAddComment} style={styles.smallSendButton}>
          <Send size={16} color="#ffffff" />
        </Pressable>
      </View>
    </View>
  );
}

function ServicesScreen({
  accessSettings,
  friendsList,
  isNewConvModalVisible,
  messageDraft,
  messageThreads,
  messages,
  onSendMessage,
  onSearchRestaurants,
  onStartConversation,
  onToggleAccess,
  onUpdatePrivacy,
  restaurants,
  restaurantSearchError,
  restaurantSearchLoading,
  selectedConversationId,
  serviceView,
  setIsNewConvModalVisible,
  setMessageDraft,
  setSelectedConversationId,
  setServiceView,
  settings,
  onLogout,
}) {
  return (
    <View style={styles.servicesLayout}>
      <View style={styles.serviceTabs}>
        <ServiceTab Icon={MessageCircle} active={serviceView === "messages"} id="messages" label="Messages" setServiceView={setServiceView} />
        <ServiceTab Icon={ChefHat} active={serviceView === "restaurants"} id="restaurants" label="Restos" setServiceView={setServiceView} />
        <ServiceTab Icon={ShieldCheck} active={serviceView === "access"} id="access" label="Accès" setServiceView={setServiceView} />
      </View>
      {serviceView === "messages" ? (
        <MessagesScreen
          friendsList={friendsList}
          isNewConvModalVisible={isNewConvModalVisible}
          messageDraft={messageDraft}
          messageThreads={messageThreads}
          messages={messages}
          onSendMessage={onSendMessage}
          onStartConversation={onStartConversation}
          selectedConversationId={selectedConversationId}
          setIsNewConvModalVisible={setIsNewConvModalVisible}
          setMessageDraft={setMessageDraft}
          setSelectedConversationId={setSelectedConversationId}
        />
      ) : null}
      {serviceView === "restaurants" ? (
        <RestaurantsScreen
          onSearchRestaurants={onSearchRestaurants}
          restaurants={restaurants}
          restaurantSearchError={restaurantSearchError}
          restaurantSearchLoading={restaurantSearchLoading}
        />
      ) : null}
      {serviceView === "access" ? (
        <AccessScreen
          accessSettings={accessSettings}
          onToggleAccess={onToggleAccess}
          onUpdatePrivacy={onUpdatePrivacy}
          settings={settings}
        />
      ) : null}
      {onLogout ? (
        <Pressable onPress={onLogout} style={styles.logoutButton}>
          <Text style={styles.logoutButtonText}>Se déconnecter</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

function ServiceTab({ Icon, active, id, label, setServiceView }) {
  return (
    <Pressable onPress={() => setServiceView(id)} style={[styles.serviceTab, active && styles.serviceTabActive]}>
      <Icon size={16} color={active ? "#0f766e" : "#64748b"} />
      <Text style={[styles.serviceTabText, active && styles.serviceTabTextActive]}>{label}</Text>
    </Pressable>
  );
}

function RestaurantsScreen({ onSearchRestaurants, restaurants, restaurantSearchError, restaurantSearchLoading }) {
  const [restaurantSearch, setRestaurantSearch] = useState("");
  const emptyRestaurantText = restaurantSearchLoading
    ? "Recherche en cours..."
    : "Aucun restaurant ne correspond à cette recherche.";

  useEffect(() => {
    const timeout = setTimeout(() => {
      onSearchRestaurants(restaurantSearch);
    }, 450);
    return () => clearTimeout(timeout);
  }, [restaurantSearch, onSearchRestaurants]);

  return (
    <FlatList
      contentContainerStyle={styles.innerListContent}
      data={restaurants}
      keyExtractor={(item) => String(item.thefork_restaurant_id ?? item.id)}
      ListHeaderComponent={
        <>
          <View style={styles.searchInputWrap}>
            <Search size={17} color="#64748b" />
            <TextInput
              onChangeText={setRestaurantSearch}
              placeholder="Rechercher un restaurant ou une cuisine"
              placeholderTextColor="#94a3b8"
              style={styles.searchInput}
              value={restaurantSearch}
            />
            {restaurantSearchLoading ? <ActivityIndicator color="#0f766e" size="small" /> : null}
          </View>
          {restaurantSearchError ? <Text style={styles.errorInline}>{restaurantSearchError}</Text> : null}
          <Text style={styles.scoreLegend}>
            Score basé sur la cuisine, les options légumes/protéines, les tags végétariens et les points à limiter
            comme friture, fast-food ou desserts.
          </Text>
        </>
      }
      ListEmptyComponent={<Text style={styles.emptySearchText}>{emptyRestaurantText}</Text>}
      renderItem={({ item }) => (
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <View style={styles.flex}>
              <Text style={styles.cardTitle}>{item.name}</Text>
              <Text style={styles.cardMeta}>{item.area}</Text>
            </View>
            <Text style={styles.scoreBadge}>{item.diabetes_friendly_score}</Text>
          </View>
          <View style={styles.restaurantMetaRow}>
            <Text style={styles.achievementLabel}>{item.best_for}</Text>
            {item.price_range ? <Text style={styles.priceBadge}>{item.price_range}</Text> : null}
          </View>
          <Text style={styles.cardBody}>{item.notes}</Text>
        </View>
      )}
    />
  );
}

function MessagesScreen({
  friendsList,
  isNewConvModalVisible,
  messageDraft,
  messageThreads,
  messages,
  onSendMessage,
  onStartConversation,
  selectedConversationId,
  setIsNewConvModalVisible,
  setMessageDraft,
  setSelectedConversationId,
}) {
  const selectedConversation = messages.find((message) => message.id === selectedConversationId) ?? messages[0];
  const thread = selectedConversation ? messageThreads[selectedConversation.id] ?? [] : [];
  const availableFriends = (friendsList ?? []).filter(
    (f) => !messages.some((m) => m.contact_name === f.name),
  );

  return (
    <View style={styles.messageLayout}>
      <View style={styles.conversationHeader}>
        <Pressable
          onPress={() => setIsNewConvModalVisible(true)}
          style={styles.newConvButton}
        >
          <Plus size={16} color="#0f766e" />
          <Text style={styles.newConvButtonText}>Nouvelle conversation</Text>
        </Pressable>
      </View>

      {isNewConvModalVisible ? (
        <View style={styles.newConvPanel}>
          <View style={styles.newConvPanelHeader}>
            <Text style={styles.cardTitle}>Écrire à un ami</Text>
            <Pressable onPress={() => setIsNewConvModalVisible(false)}>
              <X size={20} color="#64748b" />
            </Pressable>
          </View>
          {availableFriends.length === 0 ? (
            <Text style={styles.cardMeta}>
              {friendsList.length === 0
                ? "Ajoute d'abord un ami depuis l'onglet Communauté."
                : "Tu as déjà une conversation avec chacun de tes amis."}
            </Text>
          ) : (
            availableFriends.map((friend) => (
              <Pressable
                key={friend.id}
                style={styles.newConvFriendRow}
                onPress={() => onStartConversation(friend.id)}
              >
                <Text style={styles.cardTitle}>{friend.name}</Text>
                {friend.primary_goal ? (
                  <Text style={styles.cardMeta}>{friend.primary_goal}</Text>
                ) : null}
              </Pressable>
            ))
          )}
        </View>
      ) : null}

      <FlatList
        horizontal
        contentContainerStyle={styles.conversationRail}
        data={messages}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <Pressable
            onPress={() => setSelectedConversationId(item.id)}
            style={[styles.conversationChip, selectedConversation?.id === item.id && styles.conversationChipActive]}
          >
            <Text style={[styles.conversationName, selectedConversation?.id === item.id && styles.conversationNameActive]}>
              {item.contact_name}
            </Text>
            {item.unread_count > 0 ? <Text style={styles.unreadBadge}>{item.unread_count}</Text> : null}
          </Pressable>
        )}
        showsHorizontalScrollIndicator={false}
      />

      <ScrollView contentContainerStyle={styles.threadContent}>
        {thread.map((message) => (
          <View key={message.id} style={[styles.messageBubble, message.fromMe && styles.messageBubbleMine]}>
            <Text style={[styles.messageText, message.fromMe && styles.messageTextMine]}>{message.text}</Text>
            <Text style={[styles.messageTime, message.fromMe && styles.messageTimeMine]}>{message.time}</Text>
          </View>
        ))}
      </ScrollView>

      <View style={styles.messageComposer}>
        <TextInput
          onChangeText={setMessageDraft}
          placeholder="Écrire un message..."
          placeholderTextColor="#94a3b8"
          style={styles.messageInput}
          value={messageDraft}
        />
        <Pressable onPress={onSendMessage} style={styles.sendButton}>
          <Send size={18} color="#ffffff" />
        </Pressable>
      </View>
    </View>
  );
}

function AccessScreen({ accessSettings, onToggleAccess, onUpdatePrivacy, settings }) {
  const isPrivate = settings.profile.privacy_level === "Données privées";

  return (
    <ScrollView contentContainerStyle={styles.innerListContent}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Confidentialité</Text>
        <Text style={styles.cardBody}>Choisis exactement ce que tu partages avec le médecin et le patient expert.</Text>
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

function SessionsScreen({ 
  sessions, 
  sessionTitle, setSessionTitle, 
  sessionKind, setSessionKind,
  sessionDate, setSessionDate,
  sessionCapacity, setSessionCapacity,
  sessionNotes, setSessionNotes,
  joinedSessions,
  onCreateSession,
  onJoinSession,
  isExpert
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
                  (hasJoined || isFull) && { backgroundColor: "#94a3b8" }
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

function MiniStat({ label, value }) {
  return (
    <View style={styles.miniStat}>
      <Text style={styles.miniStatValue}>{value}</Text>
      <Text style={styles.miniStatLabel}>{label}</Text>
    </View>
  );
}

function StatCard({ label, value }) {
  return (
    <View style={styles.statCard}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function buildThreads(conversations) {
  return conversations.reduce((threads, conversation) => {
    threads[conversation.id] = [
      {
        id: `${conversation.id}-a`,
        fromMe: false,
        text: conversation.last_message,
        time: formatDate(conversation.updated_at),
      },
      {
        id: `${conversation.id}-b`,
        fromMe: true,
        text: "Merci, je regarde ca aujourd'hui.",
        time: "Vu",
      },
    ];
    return threads;
  }, {});
}

function mergeRestaurants(restaurants) {
  const seen = new Set();
  return restaurants.filter((restaurant) => {
    const key = String(restaurant.thefork_restaurant_id ?? restaurant.id ?? restaurant.name).toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

const SERVICE_TOKEN_FALLBACK = "yalla-secret-token";
function currentAuthToken() {
  return getActiveAccessToken() ?? SERVICE_TOKEN_FALLBACK;
}

async function apiGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Authorization: `Bearer ${currentAuthToken()}`,
    },
  });
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    console.warn(`[apiGet local] ${path} -> ${response.status}  ${body.slice(0, 160)}`);
    throw new Error(`Impossible de charger les données (${response.status}).`);
  }
  return response.json();
}

async function apiPost(path, payload) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${currentAuthToken()}`,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Action impossible.");
  }
  return response.json();
}

async function apiPatch(path, payload) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${currentAuthToken()}`,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Action impossible.");
  }
  return response.json();
}

function formatDate(value) {
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short" }).format(new Date(value));
}

function YallaLogo({ size = 48 }) {
  return <Image source={YALLA_LOGO} style={{ width: size, height: size, borderRadius: size / 2 }} />;
}

function Text(props) {
  const { style, ...otherProps } = props;
  let fontFamily = 'Inter_400Regular';
  
  const flatStyle = StyleSheet.flatten(style) || {};
  const weight = flatStyle.fontWeight;
  
  if (weight === '900' || weight === '800' || weight === 'bold') {
    fontFamily = 'Outfit_700Bold';
  } else if (weight === '700' || weight === '600') {
    fontFamily = 'Outfit_600SemiBold';
  } else if (weight === '500') {
    fontFamily = 'Inter_500Medium';
  } else if (flatStyle.fontSize && flatStyle.fontSize >= 16) {
    fontFamily = 'Outfit_400Regular';
  }

  return <RNText style={[{ fontFamily }, style]} {...otherProps} />;
}

function Pressable({ onPress, onPressIn, onPressOut, style, children, ...props }) {
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
      <Animated.View style={{ transform: [{ scale }] }}>
        {children}
      </Animated.View>
    </RNPressable>
  );
}

function Skeleton({ width, height, borderRadius = 8, style }) {
  const anim = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(anim, { toValue: 0.7, duration: 800, useNativeDriver: true }),
        Animated.timing(anim, { toValue: 0.3, duration: 800, useNativeDriver: true })
      ])
    ).start();
  }, [anim]);

  return (
    <Animated.View
      style={[
        {
          width,
          height,
          borderRadius,
          backgroundColor: '#e2e8f0',
          opacity: anim,
        },
        style,
      ]}
    />
  );
}

function ScreenSkeleton({ activeTab }) {
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

