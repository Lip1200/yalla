import { useEffect, useMemo, useState, useRef } from "react";
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

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://192.168.1.18:8001";
const PATIENT_ID = 101;
const EXPERT_PATIENT_ID = 102;

const suggestedChallenges = [
  {
    id: 201,
    title: "10 min apres le repas",
    description: "Marcher doucement apres le diner pendant 4 soirs.",
    category: "Activite",
    progress: 0,
    due_on: "2026-05-06",
  },
  {
    id: 202,
    title: "Assiette equilibree",
    description: "Composer 3 repas avec legumes, proteines et feculents complets.",
    category: "Alimentation",
    progress: 0,
    due_on: "2026-05-08",
  },
];

const suggestedFriends = [
  { id: 301, name: "Nadia Benali", detail: "Marche douce, 4 defis termines" },
  { id: 302, name: "Youssef Haddad", detail: "Cuisine maison, nouveau dans le groupe" },
  { id: 303, name: "Sara Amrani", detail: "Objectif regularite, active cette semaine" },
];

const extraRestaurants = [
  {
    id: 101,
    name: "Graines & Saveurs",
    area: "Carouge",
    diabetes_friendly_score: 91,
    best_for: "Bols complets",
    notes: "Legumes rotis, quinoa, poisson grille et sauces a part.",
  },
  {
    id: 102,
    name: "Bistrot du Parc",
    area: "Paquis",
    diabetes_friendly_score: 84,
    best_for: "Sortie de groupe",
    notes: "Menu simple avec viandes grillees, salades et portions ajustables.",
  },
  {
    id: 103,
    name: "Le Levain Clair",
    area: "Plainpalais",
    diabetes_friendly_score: 79,
    best_for: "Brunch controle",
    notes: "Pain complet, oeufs, yaourt nature et fruits frais sans sirops.",
  },
];

export default function App() {
  const [fontsLoaded] = useFonts({
    Outfit_400Regular,
    Outfit_600SemiBold,
    Outfit_700Bold,
    Inter_400Regular,
    Inter_500Medium,
  });

  const [activePatientId, setActivePatientId] = useState(PATIENT_ID);
  const [activeTab, setActiveTab] = useState("home");
  const [serviceView, setServiceView] = useState("messages");
  const [profile, setProfile] = useState(null);
  const [feed, setFeed] = useState([]);
  const [progression, setProgression] = useState(null);
  const [restaurants, setRestaurants] = useState([]);
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
      { id: "progress", label: "Defis", icon: Target },
      { id: "community", label: "Communaute", icon: Users },
      { id: "services", label: "Services", icon: Settings },
    ];

    baseTabs.splice(3, 0, { id: "sessions", label: "Seances", icon: CalendarPlus });

    return baseTabs;
  }, [isExpert]);

  useEffect(() => {
    loadApp();
  }, [activePatientId]);

  async function loadApp() {
    setLoading(true);

    try {
      const [profileData, feedData, progressionData, restaurantData, messageData, settingsData] = await Promise.all([
        apiGet(`/api/patients/${activePatientId}/profile`),
        apiGet(`/api/patients/${activePatientId}/feed`),
        apiGet(`/api/patients/${activePatientId}/progression`),
        apiGet("/api/restaurants/recommendations"),
        apiGet(`/api/patients/${activePatientId}/messages`),
        apiGet(`/api/patients/${activePatientId}/settings`),
      ]);

      setProfile(profileData);
      setFeed(feedData);
      setProgression(progressionData);
      setRestaurants([...restaurantData, ...extraRestaurants]);
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
      Alert.alert("Erreur", error.message);
    } finally {
      setLoading(false);
    }
  }

  async function createPost() {
    if (!postContent.trim() && !postImageBase64) {
      Alert.alert("Publication vide", "Ecris quelque chose ou ajoute une photo avant de publier.");
      return;
    }

    try {
      const payload = {
        type: postType,
        content: postContent.trim() || "📸 Photo partagée",
        achievement_label: postType === "achievement" ? "Nouvelle reussite" : null,
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
      Alert.alert("Champs manquants", "Ajoutez un titre, une date et une capacite.");
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
      Alert.alert("Succes", "Seance organisee avec succes !");
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
      Alert.alert("Succes", "Vous avez rejoint la seance !");
    } catch (error) {
      Alert.alert("Erreur", "Impossible de rejoindre la seance.");
    }
  }

  async function updatePrivacy(isPrivate) {
    try {
      const nextSettings = await apiPatch(`/api/patients/${activePatientId}/settings/privacy`, {
        privacy_level: isPrivate ? "Donnees privees" : "Partage selectif",
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

  function toggleAccess(key) {
    setAccessSettings((current) => ({ ...current, [key]: !current[key] }));
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

  function joinChallenge(challenge) {
    setJoinedChallengeIds((current) => new Set(current).add(challenge.id));
  }

  function addFriend(friendId) {
    setFriendIds((current) => new Set(current).add(friendId));
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
          <ActivityIndicator color="#0f766e" size="large" />
          <RNText style={styles.loadingText}>Yalla</RNText>
        </SafeAreaView>
      </SafeAreaProvider>
    );
  }

  const isLoadingApp = loading || !profile || !progression || !settings || !accessSettings;

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.screen}>
        <StatusBar style="dark" />
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Bonjour</Text>
            {profile ? (
              <Text style={styles.userName}>{profile.full_name}</Text>
            ) : (
              <Skeleton width={150} height={28} style={{ marginTop: 4 }} />
            )}
          </View>
          <Pressable
            onPress={() => setActivePatientId(isExpert ? PATIENT_ID : EXPERT_PATIENT_ID)}
            style={styles.roleSwitch}
          >
            <Text style={styles.roleSwitchText}>{isExpert ? "Expert" : "Patient"}</Text>
          </Pressable>
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
    if (activeTab === "home") {
      return <HomeScreen progression={progression} profile={profile} setActiveTab={setActiveTab} />;
    }
    if (activeTab === "progress") {
      return (
        <ProgressScreen
          joinedChallengeIds={joinedChallengeIds}
          onJoinChallenge={joinChallenge}
          progression={progression}
        />
      );
    }
    if (activeTab === "community") {
      return (
        <CommunityScreen
          commentInputs={commentInputs}
          commentsByPost={commentsByPost}
          feed={feed}
          friendIds={friendIds}
          likedPosts={likedPosts}
          onAddComment={addComment}
          onAddFriend={addFriend}
          onCreatePost={createPost}
          onToggleLike={toggleLike}
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
          messageDraft={messageDraft}
          messageThreads={messageThreads}
          messages={messages}
          onSendMessage={sendMessage}
          onToggleAccess={toggleAccess}
          onUpdatePrivacy={updatePrivacy}
          restaurants={restaurants}
          selectedConversationId={selectedConversationId}
          serviceView={serviceView}
          setMessageDraft={setMessageDraft}
          setSelectedConversationId={setSelectedConversationId}
          setServiceView={setServiceView}
          settings={settings}
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
  const nextChallenge = progression.active_challenges[0];

  return (
    <ScrollView contentContainerStyle={styles.listContent}>
      <View style={styles.heroCard}>
        <Text style={styles.heroKicker}>Objectif du moment</Text>
        <Text style={styles.heroText}>{profile.main_goal}</Text>
        <View style={styles.heroStats}>
          <MiniStat label="minutes" value={profile.weekly_activity_minutes} />
          <MiniStat label="defis" value={`${profile.challenge_completion_rate}%`} />
        </View>
      </View>

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Aujourd'hui</Text>
        <Pressable onPress={() => setActiveTab("progress")}>
          <Text style={styles.linkText}>Voir defis</Text>
        </Pressable>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>{nextChallenge?.title ?? "Choisir un defi"}</Text>
        <Text style={styles.cardBody}>
          {nextChallenge?.description ?? "Rejoins un defi simple pour garder le rythme cette semaine."}
        </Text>
        {nextChallenge ? (
          <>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${nextChallenge.progress}%` }]} />
            </View>
            <Text style={styles.cardFooter}>{nextChallenge.progress}% termine</Text>
          </>
        ) : null}
      </View>
    </ScrollView>
  );
}

function ProgressScreen({ joinedChallengeIds, onJoinChallenge, progression }) {
  const joinedSuggestions = suggestedChallenges.filter((challenge) => joinedChallengeIds.has(challenge.id));
  const availableSuggestions = suggestedChallenges.filter((challenge) => !joinedChallengeIds.has(challenge.id));
  const activeChallenges = [...progression.active_challenges, ...joinedSuggestions];

  return (
    <ScrollView contentContainerStyle={styles.listContent}>
      <View style={styles.statsRow}>
        <StatCard label="Minutes" value={progression.weekly_activity_minutes} />
        <StatCard label="Defis" value={`${progression.challenge_completion_rate}%`} />
        <StatCard label="Serie" value={`${progression.current_streak_days}j`} />
      </View>

      <Text style={styles.sectionTitle}>Mes defis</Text>
      {activeChallenges.map((challenge) => (
        <ChallengeCard key={challenge.id} challenge={challenge} />
      ))}

      <Text style={styles.sectionTitle}>Rejoindre un defi</Text>
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
          <Text style={styles.cardFooter}>Echeance {formatDate(challenge.due_on)}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

function ChallengeCard({ challenge }) {
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>{challenge.title}</Text>
      <Text style={styles.cardMeta}>{challenge.category}</Text>
      <Text style={styles.cardBody}>{challenge.description}</Text>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: `${challenge.progress}%` }]} />
      </View>
      <Text style={styles.cardFooter}>{challenge.progress}% · echeance {formatDate(challenge.due_on)}</Text>
    </View>
  );
}

function CommunityScreen({
  commentInputs,
  commentsByPost,
  feed,
  friendIds,
  likedPosts,
  onAddComment,
  onAddFriend,
  onCreatePost,
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
          <Text style={styles.sectionTitle}>Ajouter des amis</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.friendRail}>
            {suggestedFriends.map((friend) => (
              <View key={friend.id} style={styles.friendCard}>
                <Text style={styles.cardTitle}>{friend.name}</Text>
                <Text style={styles.cardMeta}>{friend.detail}</Text>
                <Pressable onPress={() => onAddFriend(friend.id)} style={styles.secondaryButton}>
                  <UserPlus size={16} color="#0f766e" />
                  <Text style={styles.secondaryButtonText}>{friendIds.has(friend.id) ? "Ajoute" : "Ajouter"}</Text>
                </Pressable>
              </View>
            ))}
          </ScrollView>
          <Text style={styles.sectionTitle}>Fil d'activite</Text>
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
          <Text style={[styles.segmentText, postType === "achievement" && styles.segmentTextActive]}>Reussite</Text>
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
  messageDraft,
  messageThreads,
  messages,
  onSendMessage,
  onToggleAccess,
  onUpdatePrivacy,
  restaurants,
  selectedConversationId,
  serviceView,
  setMessageDraft,
  setSelectedConversationId,
  setServiceView,
  settings,
}) {
  return (
    <View style={styles.servicesLayout}>
      <View style={styles.serviceTabs}>
        <ServiceTab Icon={MessageCircle} active={serviceView === "messages"} id="messages" label="Messages" setServiceView={setServiceView} />
        <ServiceTab Icon={ChefHat} active={serviceView === "restaurants"} id="restaurants" label="Restos" setServiceView={setServiceView} />
        <ServiceTab Icon={ShieldCheck} active={serviceView === "access"} id="access" label="Acces" setServiceView={setServiceView} />
      </View>
      {serviceView === "messages" ? (
        <MessagesScreen
          messageDraft={messageDraft}
          messageThreads={messageThreads}
          messages={messages}
          onSendMessage={onSendMessage}
          selectedConversationId={selectedConversationId}
          setMessageDraft={setMessageDraft}
          setSelectedConversationId={setSelectedConversationId}
        />
      ) : null}
      {serviceView === "restaurants" ? <RestaurantsScreen restaurants={restaurants} /> : null}
      {serviceView === "access" ? (
        <AccessScreen
          accessSettings={accessSettings}
          onToggleAccess={onToggleAccess}
          onUpdatePrivacy={onUpdatePrivacy}
          settings={settings}
        />
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

function RestaurantsScreen({ restaurants }) {
  return (
    <FlatList
      contentContainerStyle={styles.innerListContent}
      data={restaurants}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => (
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <View style={styles.flex}>
              <Text style={styles.cardTitle}>{item.name}</Text>
              <Text style={styles.cardMeta}>{item.area}</Text>
            </View>
            <Text style={styles.scoreBadge}>{item.diabetes_friendly_score}</Text>
          </View>
          <Text style={styles.achievementLabel}>{item.best_for}</Text>
          <Text style={styles.cardBody}>{item.notes}</Text>
        </View>
      )}
    />
  );
}

function MessagesScreen({
  messageDraft,
  messageThreads,
  messages,
  onSendMessage,
  selectedConversationId,
  setMessageDraft,
  setSelectedConversationId,
}) {
  const selectedConversation = messages.find((message) => message.id === selectedConversationId) ?? messages[0];
  const thread = selectedConversation ? messageThreads[selectedConversation.id] ?? [] : [];

  return (
    <View style={styles.messageLayout}>
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
          placeholder="Ecrire un message..."
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
  const isPrivate = settings.profile.privacy_level === "Donnees privees";

  return (
    <ScrollView contentContainerStyle={styles.innerListContent}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Confidentialite</Text>
        <Text style={styles.cardBody}>Choisis exactement ce que tu partages avec le medecin et le patient expert.</Text>
        <View style={styles.settingRow}>
          <View style={styles.settingText}>
            <Text style={styles.settingTitle}>Mode prive global</Text>
            <Text style={styles.cardMeta}>Desactive les partages principaux sans supprimer les choix fins.</Text>
          </View>
          <Switch value={isPrivate} onValueChange={onUpdatePrivacy} thumbColor={isPrivate ? "#0f766e" : "#f8fafc"} />
        </View>
      </View>

      <AccessToggle
        description="Minutes d'activite, serie et progression generale."
        label="Activite physique"
        onToggle={() => onToggleAccess("share_activity")}
        value={accessSettings.share_activity}
      />
      <AccessToggle
        description="Defis rejoints, progression et badges."
        label="Defis"
        onToggle={() => onToggleAccess("share_challenges")}
        value={accessSettings.share_challenges}
      />
      <AccessToggle
        description="Restaurants consultes ou recommandes."
        label="Restaurants"
        onToggle={() => onToggleAccess("share_restaurants")}
        value={accessSettings.share_restaurants}
      />
      <AccessToggle
        description="Posts, commentaires et likes dans la communaute."
        label="Activite sociale"
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
          <Text style={styles.cardTitle}>Organiser une seance</Text>
          <TextInput
            onChangeText={setSessionTitle}
            placeholder="Titre de la seance"
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
            placeholder="Capacite (ex: 10)"
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
            <Text style={styles.primaryButtonText}>Creer la seance</Text>
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
              {session.kind === "group" ? "Groupe" : "Individuel"} · {session.enrolled_count}/{session.capacity} places
            </Text>
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

async function apiGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Authorization": "Bearer yalla-secret-token"
    }
  });
  if (!response.ok) {
    throw new Error("Impossible de charger les donnees.");
  }
  return response.json();
}

async function apiPost(path, payload) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "Authorization": "Bearer yalla-secret-token"
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
      "Authorization": "Bearer yalla-secret-token"
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

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: "#f7f8f5",
  },
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#f7f8f5",
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
    paddingBottom: 10,
    paddingTop: 10,
  },
  greeting: {
    color: "#64748b",
    fontSize: 13,
    fontWeight: "700",
  },
  userName: {
    color: "#13201f",
    fontSize: 23,
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
  flex: {
    flex: 1,
  },
  stack: {
    gap: 14,
  },
  listContent: {
    gap: 14,
    padding: 16,
    paddingBottom: 98,
  },
  innerListContent: {
    gap: 14,
    padding: 16,
    paddingBottom: 112,
  },
  heroCard: {
    borderRadius: 8,
    backgroundColor: "#123331",
    padding: 18,
  },
  heroKicker: {
    color: "#b8d9d4",
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  heroText: {
    color: "#ffffff",
    fontSize: 20,
    fontWeight: "800",
    lineHeight: 27,
    marginTop: 8,
  },
  heroStats: {
    flexDirection: "row",
    gap: 10,
    marginTop: 16,
  },
  miniStat: {
    borderRadius: 8,
    backgroundColor: "rgba(255,255,255,0.12)",
    paddingHorizontal: 12,
    paddingVertical: 9,
  },
  miniStatValue: {
    color: "#ffffff",
    fontSize: 17,
    fontWeight: "900",
  },
  miniStatLabel: {
    color: "#cde4e0",
    fontSize: 11,
    fontWeight: "800",
    marginTop: 2,
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  sectionTitle: {
    color: "#13201f",
    fontSize: 16,
    fontWeight: "900",
  },
  linkText: {
    color: "#0f766e",
    fontSize: 13,
    fontWeight: "900",
  },
  card: {
    borderRadius: 8,
    backgroundColor: "#ffffff",
    padding: 15,
    shadowColor: "#0f172a",
    shadowOpacity: 0.06,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 5 },
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
    fontSize: 16,
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
  scoreBadge: {
    minWidth: 40,
    borderRadius: 8,
    backgroundColor: "#dcfce7",
    color: "#166534",
    fontSize: 14,
    fontWeight: "900",
    overflow: "hidden",
    paddingHorizontal: 8,
    paddingVertical: 7,
    textAlign: "center",
  },
  statsRow: {
    flexDirection: "row",
    gap: 10,
  },
  statCard: {
    flex: 1,
    borderRadius: 8,
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
    borderRadius: 8,
    backgroundColor: "#e2e8f0",
    marginTop: 14,
    padding: 4,
  },
  segment: {
    flex: 1,
    alignItems: "center",
    borderRadius: 6,
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
    minHeight: 102,
    borderRadius: 8,
    backgroundColor: "#f8fafc",
    color: "#13201f",
    fontSize: 15,
    lineHeight: 22,
    marginTop: 14,
    padding: 12,
    textAlignVertical: "top",
  },
  input: {
    borderRadius: 8,
    backgroundColor: "#f8fafc",
    color: "#13201f",
    fontSize: 15,
    marginTop: 14,
    padding: 12,
  },
  primaryButton: {
    alignItems: "center",
    borderRadius: 8,
    backgroundColor: "#0f766e",
    marginTop: 14,
    paddingVertical: 13,
  },
  primaryButtonText: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "900",
  },
  secondaryButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    borderRadius: 8,
    backgroundColor: "#ecfdf5",
    marginTop: 12,
    paddingVertical: 9,
  },
  secondaryButtonText: {
    color: "#0f766e",
    fontSize: 13,
    fontWeight: "900",
  },
  iconButton: {
    alignItems: "center",
    justifyContent: "center",
    width: 38,
    height: 38,
    borderRadius: 8,
    backgroundColor: "#0f766e",
  },
  friendRail: {
    gap: 12,
    paddingRight: 16,
  },
  friendCard: {
    width: 210,
    borderRadius: 8,
    backgroundColor: "#ffffff",
    padding: 14,
  },
  actionRow: {
    flexDirection: "row",
    gap: 10,
    marginTop: 14,
  },
  actionButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderRadius: 999,
    backgroundColor: "#f1f5f9",
    paddingHorizontal: 11,
    paddingVertical: 7,
  },
  actionButtonActive: {
    backgroundColor: "#ffe4e6",
  },
  actionText: {
    color: "#64748b",
    fontSize: 13,
    fontWeight: "900",
  },
  actionTextActive: {
    color: "#be123c",
  },
  commentBubble: {
    borderLeftWidth: 3,
    borderLeftColor: "#ccfbf1",
    marginTop: 12,
    paddingLeft: 10,
  },
  commentAuthor: {
    color: "#0f766e",
    fontSize: 12,
    fontWeight: "900",
  },
  commentText: {
    color: "#334155",
    fontSize: 13,
    lineHeight: 19,
    marginTop: 2,
  },
  commentComposer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 12,
  },
  commentInput: {
    flex: 1,
    borderRadius: 8,
    backgroundColor: "#f8fafc",
    color: "#13201f",
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  smallSendButton: {
    alignItems: "center",
    justifyContent: "center",
    width: 38,
    height: 38,
    borderRadius: 8,
    backgroundColor: "#0f766e",
  },
  servicesLayout: {
    flex: 1,
  },
  serviceTabs: {
    flexDirection: "row",
    gap: 8,
    paddingHorizontal: 16,
    paddingBottom: 6,
  },
  serviceTab: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    borderRadius: 8,
    backgroundColor: "#e2e8f0",
    paddingVertical: 10,
  },
  serviceTabActive: {
    backgroundColor: "#ffffff",
  },
  serviceTabText: {
    color: "#64748b",
    fontSize: 12,
    fontWeight: "900",
  },
  serviceTabTextActive: {
    color: "#0f766e",
  },
  messageLayout: {
    flex: 1,
  },
  conversationRail: {
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  conversationChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderRadius: 8,
    backgroundColor: "#ffffff",
    height: 44,
    paddingHorizontal: 12,
  },
  conversationChipActive: {
    backgroundColor: "#0f766e",
  },
  conversationName: {
    color: "#475569",
    fontSize: 13,
    fontWeight: "900",
  },
  conversationNameActive: {
    color: "#ffffff",
  },
  unreadBadge: {
    minWidth: 24,
    borderRadius: 999,
    backgroundColor: "#f97316",
    color: "#ffffff",
    fontSize: 12,
    fontWeight: "900",
    overflow: "hidden",
    paddingHorizontal: 7,
    paddingVertical: 3,
    textAlign: "center",
  },
  threadContent: {
    gap: 10,
    paddingHorizontal: 16,
    paddingBottom: 14,
  },
  messageBubble: {
    alignSelf: "flex-start",
    maxWidth: "82%",
    borderRadius: 8,
    backgroundColor: "#ffffff",
    padding: 12,
  },
  messageBubbleMine: {
    alignSelf: "flex-end",
    backgroundColor: "#0f766e",
  },
  messageText: {
    color: "#334155",
    fontSize: 14,
    lineHeight: 20,
  },
  messageTextMine: {
    color: "#ffffff",
  },
  messageTime: {
    color: "#94a3b8",
    fontSize: 11,
    fontWeight: "800",
    marginTop: 6,
  },
  messageTimeMine: {
    color: "#ccfbf1",
  },
  messageComposer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderTopWidth: 1,
    borderTopColor: "#e2e8f0",
    backgroundColor: "#f7f8f5",
    padding: 16,
    paddingBottom: 100,
  },
  messageInput: {
    flex: 1,
    borderRadius: 8,
    backgroundColor: "#ffffff",
    color: "#13201f",
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  sendButton: {
    alignItems: "center",
    justifyContent: "center",
    width: 44,
    height: 44,
    borderRadius: 8,
    backgroundColor: "#0f766e",
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
  settingTitle: {
    color: "#13201f",
    fontSize: 15,
    fontWeight: "900",
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
    minWidth: 56,
  },
  tabLabel: {
    color: "#64748b",
    fontSize: 10,
    fontWeight: "800",
  },
  tabLabelActive: {
    color: "#0f766e",
  },
  composerActions: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 14,
  },
  composerIconButton: {
    alignItems: "center",
    justifyContent: "center",
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "#ecfdf5",
  },
  imagePreviewContainer: {
    position: "relative",
    marginTop: 14,
    borderRadius: 12,
    overflow: "hidden",
  },
  imagePreview: {
    width: "100%",
    height: 200,
    borderRadius: 12,
  },
  clearImageBtn: {
    position: "absolute",
    top: 8,
    right: 8,
    backgroundColor: "rgba(0, 0, 0, 0.6)",
    borderRadius: 999,
    padding: 6,
  },
  feedImage: {
    width: "100%",
    aspectRatio: 4 / 3,
    borderRadius: 16,
    marginTop: 12,
  },
});
