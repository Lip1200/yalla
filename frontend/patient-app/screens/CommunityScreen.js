/**
 * CommunityScreen — Communauté tab. Composer at the top, then the
 * feed of posts, friend management (received requests, sent requests,
 * suggestions), support groups carousel and the micro-challenge launcher
 * (expert only).
 *
 * Composer + FeedCard are co-located here since they're only used by
 * this screen.
 */

import { FlatList, Image, ScrollView, TextInput, View } from "react-native";
import {
  Camera,
  Heart,
  MessageCircle,
  Plus,
  Send,
  Target,
  Trophy,
  UserPlus,
  Users,
  X,
} from "lucide-react-native";

import { Pressable, Text } from "../components/atoms";
import { styles } from "../styles";

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

export default function CommunityScreen({
  isExpert,
  groups,
  myGroups = [],
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
                <View key={req.requester_id} style={[styles.card, { marginBottom: 8 }]}>
                  <Text style={styles.cardTitle}>{req.requester_name}</Text>
                  {req.primary_goal ? <Text style={styles.cardMeta}>{req.primary_goal}</Text> : null}
                  <View style={{ flexDirection: "row", gap: 8, marginTop: 10 }}>
                    <Pressable onPress={() => onAcceptFriend(req.requester_id)} style={[styles.primaryButton, { flex: 1 }]}>
                      <Text style={styles.primaryButtonText}>Accepter</Text>
                    </Pressable>
                    <Pressable onPress={() => onRejectFriend(req.requester_id)} style={[styles.secondaryButton, { flex: 1 }]}>
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
                <View key={req.id} style={[styles.card, { marginBottom: 8 }]}>
                  <Text style={styles.cardTitle}>{req.name}</Text>
                  {req.primary_goal ? <Text style={styles.cardMeta}>{req.primary_goal}</Text> : null}
                  <Text style={[styles.cardMeta, { fontStyle: "italic", marginTop: 4 }]}>
                    En attente d'acceptation
                  </Text>
                  <Pressable onPress={() => onCancelSentRequest(req.id)} style={[styles.secondaryButton, { marginTop: 10 }]}>
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

          {myGroups.length > 0 ? (
            <>
              <Text style={styles.sectionTitle}>Mes groupes</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.friendRail}>
                {myGroups.map((group) => (
                  <View key={`mine-${group.id}`} style={[styles.friendCard, styles.groupCard]}>
                    <Text style={styles.cardTitle} numberOfLines={1}>{group.name}</Text>
                    <Text style={styles.cardMeta}>
                      {group.category === "walking" ? "Marche" : group.category === "cooking" ? "Cuisine" : group.category === "support" ? "Soutien" : "Général"}
                      {" · "}
                      {group.member_count} membre(s)
                    </Text>
                    <Text style={styles.cardBody} numberOfLines={3}>{group.description}</Text>
                    <View style={{ flex: 1 }} />
                    <Text style={[styles.cardMeta, { color: "#0f766e", fontWeight: "700", marginTop: 8 }]}>✓ Membre</Text>
                  </View>
                ))}
              </ScrollView>
            </>
          ) : null}

          <Text style={styles.sectionTitle}>Groupes de soutien</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.friendRail}>
            {isExpert && (
              <View style={[styles.friendCard, styles.groupCard]}>
                <Pressable
                  onPress={() => setIsGroupFormVisible(true)}
                  style={[styles.secondaryButton, { flex: 1, justifyContent: "center", backgroundColor: "#f8fafc", borderColor: "#cbd5e1", borderWidth: 1, borderStyle: "dashed" }]}
                >
                  <Plus size={24} color="#0f766e" />
                  <Text style={[styles.secondaryButtonText, { marginTop: 8, fontSize: 13, color: "#475569" }]}>Créer un groupe</Text>
                </Pressable>
              </View>
            )}
            {groups.map((group) => (
              <View key={group.id} style={[styles.friendCard, styles.groupCard]}>
                <Text style={styles.cardTitle} numberOfLines={1}>{group.name}</Text>
                <Text style={styles.cardMeta}>
                  {group.category === "walking" ? "Marche" : group.category === "cooking" ? "Cuisine" : group.category === "support" ? "Soutien" : "Général"}
                  {" · "}
                  {group.member_count} membre(s)
                </Text>
                <Text style={styles.cardBody} numberOfLines={3}>{group.description}</Text>
                <View style={{ flex: 1 }} />
                <Pressable onPress={() => onJoinGroup(group.id)} style={[styles.primaryButton, { marginTop: 10 }]}>
                  <Text style={styles.primaryButtonText}>Rejoindre</Text>
                </Pressable>
                {isExpert && (
                  <Pressable onPress={() => setChallengeGroupTarget(group.id)} style={[styles.secondaryButton, { marginTop: 8 }]}>
                    <Target size={16} color="#0f766e" />
                    <Text style={styles.secondaryButtonText}>Lancer un défi</Text>
                  </Pressable>
                )}
              </View>
            ))}
          </ScrollView>

          {challengeGroupTarget && (
            <View style={styles.card}>
              <View style={[styles.cardHeader, { marginBottom: 16 }]}>
                <View style={{ flexDirection: "row", alignItems: "center" }}>
                  <Target size={20} color="#0f766e" style={{ marginRight: 8 }} />
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
                style={[styles.input, { marginTop: 12 }]}
                value={microChallengeDesc}
              />
              <Pressable onPress={onLaunchMicroChallenge} style={[styles.primaryButton, { marginTop: 16, backgroundColor: "#0f766e" }]}>
                <Text style={styles.primaryButtonText}>Envoyer le défi</Text>
              </Pressable>
            </View>
          )}

          {isGroupFormVisible && (
            <View style={styles.card}>
              <View style={[styles.cardHeader, { marginBottom: 16 }]}>
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
                style={[styles.input, { marginTop: 12 }]}
                value={newGroupDescription}
              />
              <View style={[styles.segmented, { marginTop: 12, marginBottom: 16, backgroundColor: "#f1f5f9" }]}>
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
