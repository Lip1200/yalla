# Patient App

Application mobile React Native avec Expo pour les patients et patients experts.

Navigation patient :

- Accueil
- Défis
- Communauté
- Services

Le patient expert voit un onglet supplémentaire :

- Séances

Les services regroupent les conversations, les recommandations de restaurants et la gestion fine des accès aux données.

## Lancement

```bash
npm install
npm start
```

Pour appeler le backend depuis un téléphone physique, lancez l'API sur le réseau local :

```bash
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```

Puis lancez Expo avec l'IP locale de l'ordinateur :

```bash
$env:EXPO_PUBLIC_API_BASE_URL="http://192.168.1.18:8001"
npm start
```

Pour tester en web sur le PC :

```bash
$env:EXPO_PUBLIC_API_BASE_URL="http://127.0.0.1:8001"
npm start
```

Puis appuyez sur `w`.

## Capteurs natifs (Phase 1 — Expo Go compatible)

L'app utilise `expo-sensors` (podomètre) et `expo-location` (GPS) — tous deux nativement inclus dans Expo Go, **pas besoin de Dev Build** pour cette phase.

### Architecture

```
services/
├── api.js         → wrappers apiGet/apiPost vers le backend
├── pedometer.js   → permission, lecture today, watch live
└── location.js    → permission, getCurrentCoords (fallback Genève)

components/
└── PedometerCard.js → composant drop-in pour ProgressScreen
```

### Permissions OS

iOS (déclarées dans `app.json` → `expo.ios.infoPlist`) :
- `NSMotionUsageDescription` — suivi des pas via CMPedometer
- `NSLocationWhenInUseUsageDescription` — restos proches

Android (déclarées dans `app.json` → `expo.android.permissions`) :
- `ACTIVITY_RECOGNITION` — accès au compteur de pas
- `ACCESS_FINE_LOCATION` / `ACCESS_COARSE_LOCATION` — GPS

Au premier lancement, Expo demande à l'utilisateur via les popups système standards.

### Limitations

- Le podomètre lit le capteur du téléphone, **pas** les données agrégées de Apple Health / Health Connect. Pour récupérer les pas mesurés par un Garmin / Apple Watch / Fitbit connectés, il faut passer en Dev Build (cf. issue #34) et utiliser `react-native-health` / `react-native-health-connect` (cf. issue #23).
- Sur Android, `Pedometer.getStepCountAsync` ne remonte que les pas depuis le dernier reboot (limitation du sensor manager). iOS supporte ~7 jours d'historique.
- Le tracking en arrière-plan nécessite des permissions supplémentaires et un Dev Build.

### Flow podomètre intégré

1. L'utilisateur va dans l'onglet **Défis**.
2. La carte "Mon activité" demande la permission de suivi des pas.
3. Une fois activée, le compteur live se met à jour à chaque pas détecté.
4. Bouton **"Synchroniser avec Yalla"** :
   - Récupère le dernier défi actif `target_unit='steps'` du patient via `GET /api/challenges/assignments/patient/{id}`.
   - POST les pas vers `/api/challenges/assignments/{id}/log` (cf. issue #22).
   - Affiche la progression mise à jour + les badges éventuellement débloqués.
5. Bouton **"Localiser pour les restos proches"** — récupère la position GPS pour personnaliser les recommandations Overpass.

## Flow setup compte invité par médecin (#37)

Quand un médecin crée un compte patient via le `doctor-web`, le backend (cf. issue #33) renvoie un `invitation_url` du type :

```
http://app.yalla/setup?token=<32-bytes-random>
```

Le médecin transmet cette URL au patient (mail, SMS, en présence). À l'ouverture :

1. **Détection automatique** : l'app intercepte l'URL via `expo-linking` et passe directement à l'écran `SetupAccountScreen`. Le token est pré-rempli.
2. **Fallback manuel** : si le patient ouvre l'app puis colle l'URL dans le champ texte, le screen extrait le token quand même (regex sur `?token=…`).
3. Le patient choisit son mot de passe → `POST /api/auth/setup-password { token, password }`.
4. Sur succès, la session AuthSession retournée par le backend est stockée localement via `expo-secure-store` (`services/auth.js::saveSession`). #28 consommera cette session.
5. Mapping des erreurs :
   - 404 → "Lien introuvable"
   - 400 → "Lien déjà utilisé"
   - 410 → "Lien expiré"
   - 422 → validation Pydantic
   - 202 → "Vérifie ton email" (confirmation requise)

### Configuration deep-linking

`app.json` déclare `scheme: "yalla"` → l'OS sait que `yalla://setup?token=XXX` doit ouvrir cette app. Pour la démo en Expo Go, le scheme natif n'est pas accessible mais le fallback manuel (paste de l'URL HTTPS) fonctionne pareil.

### Limitations

- En Expo Go, le custom URL scheme `yalla://` n'est pas enregistré (c'est Expo Go qui détient les schemes système). Pour activer le vrai deep-linking : passer en Dev Build (#34).
- Le storage de session via `expo-secure-store` ne fonctionne pas sur le web → fallback mémoire (perdu au refresh).
