import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import {
  CalendarPlus,
  ChefHat,
  Home,
  MessageCircle,
  PlusCircle,
  Settings,
  Target,
  Trophy,
  Users,
} from "lucide-react-native";

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://192.168.1.18:8001";
const PATIENT_ID = 101;
const EXPERT_PATIENT_ID = 102;

export default function App() {
  const [activePatientId, setActivePatientId] = useState(PATIENT_ID);
  const [activeTab, setActiveTab] = useState("home");
  const [profile, setProfile] = useState(null);
  const [feed, setFeed] = useState([]);
  const [progression, setProgression] = useState(null);
  const [restaurants, setRestaurants] = useState([]);
  const [messages, setMessages] = useState([]);
  const [settings, setSettings] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [postContent, setPostContent] = useState("");
  const [postType, setPostType] = useState("post");
  const [sessionTitle, setSessionTitle] = useState("");

  const isExpert = profile?.role === "expert_patient";
  const tabs = useMemo(() => {
    const baseTabs = [
      { id: "home", label: "Accueil", icon: Home },
      { id: "progress", label: "Progrès", icon: Target },
      { id: "add", label: "Ajouter", icon: PlusCircle },
      { id: "restaurants", label: "Restos", icon: ChefHat },
      { id: "messages", label: "Messages", icon: MessageCircle },
      { id: "settings", label: "Réglages", icon: Settings },
    ];

    if (isExpert) {
      baseTabs.splice(5, 0, { id: "sessions", label: "Séances", icon: CalendarPlus });
    }

    return baseTabs;
  }, [isExpert]);

  useEffect(() => {
    loadApp();
  }, [activePatientId]);

  useEffect(() => {
    if (!isExpert && activeTab === "sessions") {
      setActiveTab("home");
    }
  }, [activeTab, isExpert]);

  async function loadApp() {
    setLoading(true);

    try {
      const [profileData, feedData, progressionData, restaurantData, messageData, settingsData] = await Promise.all([
        apiGet(`/api/patients/${activePatientId}/profile`),
        apiGet(`/api/patients/${activePatientId}/feed`),
        apiGet(`/api/patients/${activePatientId}/progression`),
        apiGet(`/api/patients/${activePatientId}/restaurants`),
        apiGet(`/api/patients/${activePatientId}/messages`),
        apiGet(`/api/patients/${activePatientId}/settings`),
      ]);

      setProfile(profileData);
      setFeed(feedData);
      setProgression(progressionData);
      setRestaurants(restaurantData);
      setMessages(messageData);
      setSettings(settingsData);

      if (profileData.role === "expert_patient") {
        setSessions(await apiGet(`/api/patients/${activePatientId}/sessions`));
      } else {
        setSessions([]);
      }
    } catch (error) {
      Alert.alert("Erreur", error.message);
    } finally {
      setLoading(false);
    }
  }

  async function createPost() {
    if (!postContent.trim()) {
      Alert.alert("Publication vide", "Écris quelque chose avant de publier.");
      return;
    }

    try {
      const createdPost = await apiPost(`/api/patients/${activePatientId}/feed`, {
        type: postType,
        content: postContent.trim(),
        achievement_label: postType === "achievement" ? "Nouvelle réussite" : null,
      });
      setFeed([createdPost, ...feed]);
      setPostContent("");
      setActiveTab("home");
    } catch (error) {
      Alert.alert("Erreur", error.message);
    }
  }

  async function createSession() {
    if (!sessionTitle.trim()) {
      Alert.alert("Titre manquant", "Ajoute un titre pour la séance.");
      return;
    }

    try {
      const createdSession = await apiPost(`/api/patients/${activePatientId}/sessions`, {
        title: sessionTitle.trim(),
        kind: "group",
        scheduled_for: new Date(Date.now() + 86400000).toISOString(),
        capacity: 10,
        notes: "Séance créée depuis l'application patient expert.",
      });
      setSessions([createdSession, ...sessions]);
      setSessionTitle("");
    } catch (error) {
      Alert.alert("Erreur", error.message);
    }
  }

  async function updatePrivacy(isPrivate) {
    try {
      const nextSettings = await apiPatch(`/api/patients/${activePatientId}/settings/privacy`, {
        privacy_level: isPrivate ? "Données privées" : "Partage sélectif",
      });
      setSettings(nextSettings);
      setProfile(nextSettings.profile);
    } catch (error) {
      Alert.alert("Erreur", error.message);
    }
  }

  if (loading || !profile) {
    return (
      <SafeAreaProvider>
        <SafeAreaView style={styles.centered}>
          <ActivityIndicator color="#0f766e" size="large" />
          <Text style={styles.loadingText}>Chargement de Yalla</Text>
        </SafeAreaView>
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.screen}>
        <StatusBar style="dark" />
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Bonjour</Text>
            <Text style={styles.userName}>{profile.full_name}</Text>
          </View>
          <Pressable
            onPress={() => setActivePatientId(isExpert ? PATIENT_ID : EXPERT_PATIENT_ID)}
            style={styles.roleSwitch}
          >
            <Text style={styles.roleSwitchText}>{isExpert ? "Expert" : "Patient"}</Text>
          </Pressable>
        </View>

        <View style={styles.content}>{renderTab()}</View>

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
    if (activeTab === "home") {
      return <HomeScreen feed={feed} profile={profile} />;
    }
    if (activeTab === "progress") {
      return <ProgressScreen progression={progression} />;
    }
    if (activeTab === "add") {
      return (
        <AddScreen
          postContent={postContent}
          postType={postType}
          setPostContent={setPostContent}
          setPostType={setPostType}
          onCreatePost={createPost}
        />
      );
    }
    if (activeTab === "restaurants") {
      return <RestaurantsScreen restaurants={restaurants} />;
    }
    if (activeTab === "messages") {
      return <MessagesScreen messages={messages} />;
    }
    if (activeTab === "sessions") {
      return (
        <SessionsScreen
          sessionTitle={sessionTitle}
          sessions={sessions}
          setSessionTitle={setSessionTitle}
          onCreateSession={createSession}
        />
      );
    }
    return <SettingsScreen profile={profile} settings={settings} onUpdatePrivacy={updatePrivacy} />;
  }
}

function HomeScreen({ feed, profile }) {
  return (
    <FlatList
      ListHeaderComponent={
        <View style={styles.heroCard}>
          <Text style={styles.heroTitle}>Objectif du moment</Text>
          <Text style={styles.heroText}>{profile.main_goal}</Text>
        </View>
      }
      contentContainerStyle={styles.listContent}
      data={feed}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => <FeedCard post={item} />}
    />
  );
}

function FeedCard({ post }) {
  const isAchievement = post.type === "achievement";
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
      <Text style={styles.cardFooter}>{post.likes} soutiens · {post.comments_count} commentaires</Text>
    </View>
  );
}

function ProgressScreen({ progression }) {
  return (
    <ScrollView contentContainerStyle={styles.listContent}>
      <View style={styles.statsRow}>
        <StatCard label="Minutes" value={progression.weekly_activity_minutes} />
        <StatCard label="Défis" value={`${progression.challenge_completion_rate}%`} />
        <StatCard label="Série" value={`${progression.current_streak_days}j`} />
      </View>
      {progression.active_challenges.map((challenge) => (
        <View key={challenge.id} style={styles.card}>
          <Text style={styles.cardTitle}>{challenge.title}</Text>
          <Text style={styles.cardMeta}>{challenge.category}</Text>
          <Text style={styles.cardBody}>{challenge.description}</Text>
          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${challenge.progress}%` }]} />
          </View>
          <Text style={styles.cardFooter}>{challenge.progress}% · échéance {formatDate(challenge.due_on)}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

function AddScreen({ postContent, postType, setPostContent, setPostType, onCreatePost }) {
  return (
    <ScrollView contentContainerStyle={styles.listContent}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Nouvelle publication</Text>
        <View style={styles.segmented}>
          <Pressable onPress={() => setPostType("post")} style={[styles.segment, postType === "post" && styles.segmentActive]}>
            <Text style={[styles.segmentText, postType === "post" && styles.segmentTextActive]}>Post</Text>
          </Pressable>
          <Pressable onPress={() => setPostType("achievement")} style={[styles.segment, postType === "achievement" && styles.segmentActive]}>
            <Text style={[styles.segmentText, postType === "achievement" && styles.segmentTextActive]}>Réussite</Text>
          </Pressable>
        </View>
        <TextInput
          multiline
          onChangeText={setPostContent}
          placeholder="Partage un progrès, une question ou une réussite..."
          placeholderTextColor="#94a3b8"
          style={styles.textArea}
          value={postContent}
        />
        <Pressable onPress={onCreatePost} style={styles.primaryButton}>
          <Text style={styles.primaryButtonText}>Publier</Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

function RestaurantsScreen({ restaurants }) {
  return (
    <FlatList
      contentContainerStyle={styles.listContent}
      data={restaurants}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>{item.name}</Text>
          <Text style={styles.cardMeta}>{item.area} · score {item.diabetes_friendly_score}/100</Text>
          <Text style={styles.achievementLabel}>{item.best_for}</Text>
          <Text style={styles.cardBody}>{item.notes}</Text>
        </View>
      )}
    />
  );
}

function MessagesScreen({ messages }) {
  return (
    <FlatList
      contentContainerStyle={styles.listContent}
      data={messages}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => (
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <View>
              <Text style={styles.cardTitle}>{item.contact_name}</Text>
              <Text style={styles.cardMeta}>{item.contact_role === "expert_patient" ? "Patient expert" : "Patient"}</Text>
            </View>
            {item.unread_count > 0 ? <Text style={styles.unreadBadge}>{item.unread_count}</Text> : null}
          </View>
          <Text style={styles.cardBody}>{item.last_message}</Text>
        </View>
      )}
    />
  );
}

function SessionsScreen({ sessions, sessionTitle, setSessionTitle, onCreateSession }) {
  return (
    <ScrollView contentContainerStyle={styles.listContent}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Organiser une séance</Text>
        <TextInput
          onChangeText={setSessionTitle}
          placeholder="Titre de la séance"
          placeholderTextColor="#94a3b8"
          style={styles.input}
          value={sessionTitle}
        />
        <Pressable onPress={onCreateSession} style={styles.primaryButton}>
          <Text style={styles.primaryButtonText}>Créer la séance</Text>
        </Pressable>
      </View>
      {sessions.map((session) => (
        <View key={session.id} style={styles.card}>
          <Text style={styles.cardTitle}>{session.title}</Text>
          <Text style={styles.cardMeta}>{session.kind === "group" ? "Groupe" : "Individuel"} · {session.enrolled_count}/{session.capacity}</Text>
          <Text style={styles.cardBody}>{session.notes}</Text>
          <Text style={styles.cardFooter}>{formatDate(session.scheduled_for)}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

function SettingsScreen({ profile, settings, onUpdatePrivacy }) {
  const isPrivate = profile.privacy_level === "Données privées";
  return (
    <ScrollView contentContainerStyle={styles.listContent}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Confidentialité</Text>
        <View style={styles.settingRow}>
          <View style={styles.settingText}>
            <Text style={styles.cardBody}>Mode données privées</Text>
            <Text style={styles.cardMeta}>Masque l'activité, les défis et les restaurants au suivi courant.</Text>
          </View>
          <Switch value={isPrivate} onValueChange={onUpdatePrivacy} thumbColor={isPrivate ? "#0f766e" : "#f8fafc"} />
        </View>
      </View>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Partage actuel</Text>
        <Text style={styles.cardBody}>Activité : {settings.share_activity ? "activé" : "désactivé"}</Text>
        <Text style={styles.cardBody}>Défis : {settings.share_challenges ? "activé" : "désactivé"}</Text>
        <Text style={styles.cardBody}>Restaurants : {settings.share_restaurants ? "activé" : "désactivé"}</Text>
      </View>
    </ScrollView>
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

async function apiGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error("Impossible de charger les données.");
  }
  return response.json();
}

async function apiPost(path, payload) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
    headers: { "Content-Type": "application/json" },
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

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: "#f6f7f4",
  },
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#f6f7f4",
  },
  loadingText: {
    color: "#475569",
    marginTop: 12,
    fontWeight: "700",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 18,
    paddingBottom: 12,
    paddingTop: 12,
  },
  greeting: {
    color: "#64748b",
    fontSize: 14,
    fontWeight: "700",
  },
  userName: {
    color: "#13201f",
    fontSize: 24,
    fontWeight: "800",
  },
  roleSwitch: {
    borderRadius: 999,
    backgroundColor: "#0f766e",
    paddingHorizontal: 14,
    paddingVertical: 9,
  },
  roleSwitchText: {
    color: "#ffffff",
    fontWeight: "800",
  },
  content: {
    flex: 1,
  },
  listContent: {
    gap: 14,
    padding: 18,
    paddingBottom: 105,
  },
  heroCard: {
    borderRadius: 18,
    backgroundColor: "#102a2a",
    padding: 18,
  },
  heroTitle: {
    color: "#a7c7c2",
    fontSize: 13,
    fontWeight: "800",
  },
  heroText: {
    color: "#ffffff",
    fontSize: 20,
    fontWeight: "800",
    lineHeight: 27,
    marginTop: 8,
  },
  card: {
    borderRadius: 16,
    backgroundColor: "#ffffff",
    padding: 16,
    shadowColor: "#0f172a",
    shadowOpacity: 0.08,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 2,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  cardTitle: {
    color: "#13201f",
    fontSize: 17,
    fontWeight: "800",
  },
  cardMeta: {
    color: "#64748b",
    fontSize: 13,
    marginTop: 4,
  },
  cardBody: {
    color: "#334155",
    fontSize: 15,
    lineHeight: 22,
    marginTop: 10,
  },
  cardFooter: {
    color: "#64748b",
    fontSize: 12,
    fontWeight: "700",
    marginTop: 12,
  },
  achievementLabel: {
    alignSelf: "flex-start",
    borderRadius: 999,
    backgroundColor: "#ffedd5",
    color: "#9a3412",
    fontSize: 12,
    fontWeight: "800",
    marginTop: 12,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  statsRow: {
    flexDirection: "row",
    gap: 10,
  },
  statCard: {
    flex: 1,
    borderRadius: 16,
    backgroundColor: "#ffffff",
    padding: 14,
  },
  statValue: {
    color: "#0f766e",
    fontSize: 22,
    fontWeight: "900",
  },
  statLabel: {
    color: "#64748b",
    fontSize: 12,
    fontWeight: "800",
    marginTop: 4,
  },
  progressTrack: {
    height: 9,
    borderRadius: 999,
    backgroundColor: "#e2e8f0",
    marginTop: 14,
    overflow: "hidden",
  },
  progressFill: {
    height: 9,
    borderRadius: 999,
    backgroundColor: "#0f766e",
  },
  segmented: {
    flexDirection: "row",
    borderRadius: 12,
    backgroundColor: "#e2e8f0",
    marginTop: 14,
    padding: 4,
  },
  segment: {
    flex: 1,
    alignItems: "center",
    borderRadius: 10,
    paddingVertical: 9,
  },
  segmentActive: {
    backgroundColor: "#ffffff",
  },
  segmentText: {
    color: "#64748b",
    fontWeight: "800",
  },
  segmentTextActive: {
    color: "#0f766e",
  },
  textArea: {
    minHeight: 130,
    borderRadius: 14,
    backgroundColor: "#f8fafc",
    color: "#13201f",
    fontSize: 15,
    lineHeight: 22,
    marginTop: 14,
    padding: 12,
    textAlignVertical: "top",
  },
  input: {
    borderRadius: 14,
    backgroundColor: "#f8fafc",
    color: "#13201f",
    fontSize: 15,
    marginTop: 14,
    padding: 12,
  },
  primaryButton: {
    alignItems: "center",
    borderRadius: 14,
    backgroundColor: "#0f766e",
    marginTop: 14,
    paddingVertical: 14,
  },
  primaryButtonText: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "900",
  },
  unreadBadge: {
    minWidth: 28,
    borderRadius: 999,
    backgroundColor: "#0f766e",
    color: "#ffffff",
    fontSize: 13,
    fontWeight: "900",
    overflow: "hidden",
    paddingHorizontal: 9,
    paddingVertical: 5,
    textAlign: "center",
  },
  settingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    marginTop: 10,
  },
  settingText: {
    flex: 1,
  },
  tabBar: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: "row",
    justifyContent: "space-around",
    borderTopWidth: 1,
    borderTopColor: "#e2e8f0",
    backgroundColor: "#ffffff",
    paddingBottom: 10,
    paddingTop: 9,
  },
  tabButton: {
    alignItems: "center",
    gap: 4,
    minWidth: 48,
  },
  tabLabel: {
    color: "#64748b",
    fontSize: 10,
    fontWeight: "800",
  },
  tabLabelActive: {
    color: "#0f766e",
  },
});
