/**
 * RestaurantsScreen — Services sub-tab. Debounced search box (450ms)
 * feeding the parent's onSearchRestaurants callback. Each row shows a
 * diabetes-friendly score badge + tags.
 */

import { useEffect, useState } from "react";
import { ActivityIndicator, FlatList, TextInput, View } from "react-native";
import { Search } from "lucide-react-native";

import { Text } from "../components/atoms";
import { styles } from "../styles";

export default function RestaurantsScreen({
  onSearchRestaurants,
  restaurants,
  restaurantSearchError,
  restaurantSearchLoading,
}) {
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
