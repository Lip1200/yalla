# Audit des boutons — patient-app + doctor-web

Date: 2026-05-29 • Branche: `feat/test-suite`

Classification:
- ✅ **WIRED**: l'action invoque un endpoint backend (POST/PATCH/DELETE) et la donnée persiste
- 🟡 **LOCAL**: changement d'état UI uniquement (navigation, segments, modales, formulaires)
- ❌ **MOCK**: handler de démo qui ne fait que `setState` ou `Alert`, sans persistance

## Patient-app

### `App.js` — racine

| Élément | Statut | Handler | Note |
|---|---|---|---|
| Header (logo + nom) → ouvrir profil | 🟡 | `setActiveTab("profile")` | navigation |
| Tab bar (Home/Défis/Communauté/Sessions/Services) | 🟡 | `setActiveTab(tab.id)` | navigation |

### `screens/HomeScreen.js`

| Élément | Statut | Handler | Note |
|---|---|---|---|
| « Voir défis » (link) | 🟡 | `setActiveTab("progress")` | navigation |

### `screens/ProgressScreen.js`

| Élément | Statut | Handler | Note |
|---|---|---|---|
| « + » sur défi suggéré | ✅ | `joinChallenge` → POST `/api/challenges/assignments` | idempotent backend |

### `screens/CommunityScreen.js`

| Élément | Statut | Handler | Note |
|---|---|---|---|
| Composer: switch Post/Réussite | 🟡 | `setPostType` | local |
| Composer: « Caméra » (pick image) | ✅ | `pickImage` → `ImagePicker.launchImageLibraryAsync` | natif |
| Composer: « X » clear image | 🟡 | `clearImage` | local |
| Composer: « Publier » | ✅ | `createPost` → POST `/api/social/feed` | persiste |
| Feed: ❤️ like | ❌ **MOCK** | `toggleLike` → Set local uniquement | **pas de POST** |
| Feed: « Commenter » send | ❌ **MOCK** | `addComment` → state local uniquement | **pas de POST** |
| Demandes reçues: Accepter | ✅ | `acceptFriendRequest` → POST `/accept` | persiste |
| Demandes reçues: Refuser | ✅ | `rejectFriendRequest` → POST `/reject` | persiste |
| Demandes envoyées: Annuler | ✅ | `cancelSentRequest` → DELETE friend | persiste |
| Suggestions: « Ajouter » | ✅ | `addFriend` → POST `/friends/{id}` | persiste |
| « Créer un groupe » (expert) | 🟡 | `setIsGroupFormVisible(true)` | ouvre modale |
| Group rail: « Rejoindre » | ✅ | `joinGroup` → POST `/groups/{id}/join` | persiste, 409 si déjà membre |
| Group rail: « Lancer un défi » (expert) | 🟡 | `setChallengeGroupTarget(group.id)` | ouvre modale |
| Lancer défi: « X » fermer | 🟡 | `setChallengeGroupTarget(null)` | local |
| Lancer défi: « Envoyer » | ❌ **MOCK** | `launchMicroChallenge` → Alert + reset state | **pas de POST** |
| Form nouveau groupe: catégorie | 🟡 | `setNewGroupCategory` | local |
| Form nouveau groupe: « X » fermer | 🟡 | `setIsGroupFormVisible(false)` | local |
| Form nouveau groupe: « Créer » | ✅ | `createGroup` → POST `/api/social/groups` | persiste |

### `screens/SessionsScreen.js`

| Élément | Statut | Handler | Note |
|---|---|---|---|
| « Créer la séance » (expert) | ✅ | `createSession` → POST `/api/patients/{id}/sessions` | persiste |
| « Rejoindre » sur séance | ✅ | `joinSession` → POST `/sessions/{id}/join` | persiste |

### `screens/ServicesScreen.js`

| Élément | Statut | Handler | Note |
|---|---|---|---|
| Sous-onglets Messages/Restos/Accès | 🟡 | `setServiceView(id)` | local |
| « Se déconnecter » | ✅ | `handleLogout` → POST `/api/auth/logout` + clear session | persiste |

### `screens/MessagesScreen.js`

| Élément | Statut | Handler | Note |
|---|---|---|---|
| « + Nouvelle conversation » | 🟡 | `setIsNewConvModalVisible(true)` | ouvre panel |
| Panel: « X » fermer | 🟡 | `setIsNewConvModalVisible(false)` | local |
| Panel: ami → écrire | ✅ | `startConversationWith` → POST `/messages/start` | persiste, idempotent |
| Rail: chip conversation | 🟡 | `setSelectedConversationId(item.id)` | local |
| Composer: « Envoyer » | ❌ **MOCK** | `sendMessage` → état local uniquement | **pas de POST**, le message disparaît au reload |

### `screens/RestaurantsScreen.js`

| Élément | Statut | Handler | Note |
|---|---|---|---|
| Champ recherche (debounce 450 ms) | ✅ | `onSearchRestaurants(query)` → GET Overpass via backend | persiste pas (read-only) |

### `screens/AccessScreen.js`

| Élément | Statut | Handler | Note |
|---|---|---|---|
| Switch « Mode privé global » | ✅ | `updatePrivacy` → PATCH `/settings/privacy` | persiste |
| Switch « Activité physique » | ✅ | `toggleAccess("share_activity")` → PATCH `/settings/access` | persiste |
| Switch « Défis » | ✅ | `toggleAccess("share_challenges")` → PATCH | persiste |
| Switch « Restaurants » | ✅ | `toggleAccess("share_restaurants")` → PATCH | persiste |
| Switch « Activité sociale » (share_posts) | ❌ **MOCK** | `toggleAccess("share_posts")` → state local seulement | **pas de colonne backend** (doc commit `feat(settings)`) |
| Switch « Messages avec expert » | ❌ **MOCK** | `toggleAccess("share_messages_with_expert")` → idem | **pas de colonne backend** |

### `screens/ProfileScreen.js`

| Élément | Statut | Handler | Note |
|---|---|---|---|
| « Retour à l'accueil » | 🟡 | `onClose` → `setActiveTab("home")` | navigation |
| « Se déconnecter » | ✅ | `onLogout` → POST `/auth/logout` | persiste |

### `components/LoginScreen.js`

| Élément | Statut | Handler | Note |
|---|---|---|---|
| « Se connecter » | ✅ | `handleSubmit` → POST `/api/auth/login` | persiste |
| « J'ai un code d'invitation » | 🟡 | `onStartSetup` → `setSetupToken("")` | navigation vers SetupAccount |

### `components/OnboardingScreen.js`

| Élément | Statut | Handler | Note |
|---|---|---|---|
| Welcome: « Continuer » | 🟡 | `setStep(1)` | local |
| Form: « Démarrer Yalla » | ✅ | `handleSubmit` → PATCH `/api/users/{id}` | persiste |
| Form: « ← Revenir » | 🟡 | `setStep(0)` | local |
| Privacy radio | 🟡 | `setPrivacyLevel(opt.value)` | local |

### `components/SetupAccountScreen.js`

| Élément | Statut | Handler | Note |
|---|---|---|---|
| « Valider » | ✅ | `handleSubmit` → POST `/api/auth/setup-password` | crée user auth |
| Success: « Continuer vers Yalla » | 🟡 | `onDone(session)` | navigation |

### `components/PedometerCard.js`

| Élément | Statut | Handler | Note |
|---|---|---|---|
| « Activer le podomètre » | ✅ | `handleEnable` → permissions natives | natif iOS/Android |
| « Synchroniser » | ✅ | `handleSync` → POST `/api/patients/{id}/health-observations` | persiste |
| « Localiser » | ✅ | `handleLocate` → expo-location | natif |

### `components/BadgesSection.js`

| Élément | Statut | Handler | Note |
|---|---|---|---|
| Badge press | 🟡 | `onPress?.(item)` | optional, pas câblé en haut |

---

## Doctor-web (`App.jsx`)

| Élément | Statut | Handler | Note |
|---|---|---|---|
| « Réessayer » bootstrap error | ✅ | `bootstrap` → ré-essai loadDashboard | persiste |
| « Se déconnecter » (login error) | ✅ | `handleLogout` → POST `/auth/logout` | persiste |
| « Se déconnecter » (header) | ✅ | `handleLogout` | persiste |
| « Recharger » (dashboard refresh) | ✅ | `loadDashboard` → GET dashboard | persiste pas (read) |
| Filtres patients (Tous/Expert/Avec app) | 🟡 | `onFilterChange(filter.value)` | local |
| Patient list row → sélectionner | 🟡 | `onSelect` | navigation |
| « Voir le dossier complet » | 🟡 | `onOpenProfile` | ouvre modale |
| « Sauvegarder note » | ✅ | `onSaveNote` → POST note | persiste |
| « Effacer note » | ✅ | `onDelete` → DELETE note | persiste |
| Switch « Patient expert » | ✅ | PATCH `/expert-role` | persiste, propagé au patient via polling 60s |
| Switch « Accès app » | ✅ | PATCH `/access` | persiste |
| « Créer compte patient » | ✅ | POST `/patients/accounts` | persiste + email Resend |
| « Assigner défi » | ✅ | POST `/assignments` | persiste |
| « Fermer » modale | 🟡 | `onClose` | local |

---

## Résumé exécutif

**Boutons par catégorie:**

| Catégorie | Patient-app | Doctor-web | Total |
|---|---|---|---|
| ✅ WIRED (backend persiste) | 21 | 9 | **30** |
| 🟡 LOCAL (navigation / formulaire) | 17 | 4 | **21** |
| ❌ MOCK (à connecter) | 5 | 0 | **5** |

**Boutons MOCK à connecter au backend (par priorité):**

1. ❌ **Feed like (`toggleLike`)** — POST `/api/social/feed/{post_id}/support` ; endpoint **existe déjà** (`add_support` / `remove_support`). 15 min.
2. ❌ **Feed comments (`addComment`)** — POST `/api/social/feed/{post_id}/comments` ; endpoint **n'existe pas** ; nécessite migration table `feed_post_comments` + service + router. 1h-1h30.
3. ❌ **Send message (`sendMessage`)** — POST `/api/messaging/conversations/{conv_id}/messages` ; le module `messaging/` existe (vu dans `main.py`) ; à vérifier si l'endpoint est wired. 30 min.
4. ❌ **Launch micro-challenge to group (`launchMicroChallenge`)** — pas d'endpoint backend pour les micro-défis de groupe ; nécessite design ou retrait du bouton. 1h ou retrait (5 min).
5. ❌ **Switches `share_posts` + `share_messages_with_expert`** — colonnes manquantes dans `profiles` ; migration + extension de `AccessFlagsUpdate`. 30 min.

**Total effort pour 100% câblé:** ~4h.

**Plus impactant pour la démo:** le like (#1) car visible immédiatement et l'endpoint existe.
