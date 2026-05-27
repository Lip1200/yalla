/**
 * ServicesScreen — top-level Services tab. Hosts a sub-tab bar
 * (Messages / Restos / Accès) and routes to the matching sub-screen.
 */

import { View } from "react-native";
import { ChefHat, MessageCircle, ShieldCheck } from "lucide-react-native";

import { Pressable, Text } from "../components/atoms";
import { styles } from "../styles";
import AccessScreen from "./AccessScreen";
import MessagesScreen from "./MessagesScreen";
import RestaurantsScreen from "./RestaurantsScreen";

function ServiceTab({ Icon, active, id, label, setServiceView }) {
  return (
    <Pressable onPress={() => setServiceView(id)} style={[styles.serviceTab, active && styles.serviceTabActive]}>
      <Icon size={16} color={active ? "#0f766e" : "#64748b"} />
      <Text style={[styles.serviceTabText, active && styles.serviceTabTextActive]}>{label}</Text>
    </Pressable>
  );
}

export default function ServicesScreen({
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
