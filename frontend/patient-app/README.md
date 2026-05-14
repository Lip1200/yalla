# Patient App

Application mobile React Native avec Expo pour les patients et patients experts.

Navigation patient :

- Accueil
- Defis
- Communaute
- Services

Le patient expert voit un onglet supplementaire :

- Seances

Les services regroupent les conversations, les recommandations de restaurants et la gestion fine des acces aux donnees.

## Lancement

```bash
npm install
npm start
```

Pour appeler le backend depuis un telephone physique, lancez l'API sur le reseau local :

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
