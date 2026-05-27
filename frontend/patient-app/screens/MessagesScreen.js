/**
 * MessagesScreen — Services sub-tab. Top button opens a 'Nouvelle
 * conversation' picker listing friends without an existing thread.
 * Below: horizontal rail of conversations, the active thread, and a
 * composer at the bottom. (#52 + #54)
 */

import { FlatList, ScrollView, TextInput, View } from "react-native";
import { Plus, Send, X } from "lucide-react-native";

import { Pressable, Text } from "../components/atoms";
import { styles } from "../styles";

export default function MessagesScreen({
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
        <Pressable onPress={() => setIsNewConvModalVisible(true)} style={styles.newConvButton}>
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
                {friend.primary_goal ? <Text style={styles.cardMeta}>{friend.primary_goal}</Text> : null}
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
