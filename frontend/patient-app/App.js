import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  ScrollView,
  Switch,
  TextInput,
  View,
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
import AccessScreen from "./screens/AccessScreen";
import CommunityScreen from "./screens/CommunityScreen";
import HomeScreen from "./screens/HomeScreen";
import MessagesScreen from "./screens/MessagesScreen";
import OnboardingScreen from "./components/OnboardingScreen";
import PedometerCard from "./components/PedometerCard";
import ProfileScreen from "./screens/ProfileScreen";
import ProgressScreen from "./screens/ProgressScreen";
import RestaurantsScreen from "./screens/RestaurantsScreen";
import ServicesScreen from "./screens/ServicesScreen";
import SessionsScreen from "./screens/SessionsScreen";
import SetupAccountScreen from "./components/SetupAccountScreen";
import { apiDeleteVerb, setUnauthorizedHandler } from "./services/api";
import {
  API_BASE_URL,
  apiGet,
  apiPatch,
  apiPost,
  buildThreads,
  formatDate,
  mergeRestaurants,
} from "./utils";
import {
  bootstrapSession,
  clearSession,
  logoutPatient,
  refreshSession,
} from "./services/auth";

import BadgesSection from "./components/BadgesSection";
import GroupGauge from "./components/GroupGauge";
import {
  MiniStat,
  Pressable,
  ScreenSkeleton,
  Skeleton,
  StatCard,
  Text,
  YallaLogo,
} from "./components/atoms";
import { styles } from "./styles";

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

  // Poll the lightweight surfaces (profile, progression, friend requests)
  // every 60s so doctor-side changes (role flip, app access toggle,
  // received friend request) show up without a manual reload. Full
  // loadApp would be wasteful here — we only refresh what's likely to
  // change on its own.
  useEffect(() => {
    if (!activePatientId) return;
    const interval = setInterval(async () => {
      try {
        const [fresh, freshProgression, freshRequests] = await Promise.all([
          apiGet(`/api/patients/${activePatientId}/profile`),
          apiGet(`/api/patients/${activePatientId}/progression`),
          apiGet(`/api/social/friends/${activePatientId}/requests`),
        ]);
        setProfile(fresh);
        setProgression(freshProgression);
        setFriendRequests(freshRequests ?? []);
      } catch {
        // Ignore — interval will retry. Auth errors are already handled
        // by the apiGet refresh dance.
      }
    }, 60_000);
    return () => clearInterval(interval);
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
          <Text style={styles.loadingText}>Yalla</Text>
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


