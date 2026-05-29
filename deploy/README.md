# Yalla — Production deploy on a DigitalOcean droplet

Cible : un droplet **`s-1vcpu-1gb`** (Amsterdam ou Frankfurt) avec Ubuntu 24.04, sur lequel on lance tout via **docker compose** + **Caddy** (HTTPS auto).

## Topologie

```
internet → Caddy (80/443, auto-SSL via Let's Encrypt)
              ├── /api/*, /docs   → backend  (FastAPI:8000)
              └── /, autres       → doctor-web (Nginx:80)
                                              │
                                     Supabase (déjà cloud, hors droplet)
```

Patient-app (Expo) reste mobile-only — testé via Expo Go sur téléphone, pas servi depuis le droplet.

## Pré-requis

- Un droplet DigitalOcean basic `s-1vcpu-1gb`, ~5 €/mois (le notre : `yalla-ubuntu-s-1vcpu-1gb-ams2`).
- L'IP publique du droplet (visible dans le dashboard DO).
- Accès SSH (`ssh root@<IP>`).
- Les migrations Supabase 001-012 déjà appliquées sur le projet **prod** (issue #31 — à confirmer dans le SQL editor).

## 1. Préparer le droplet (premier setup)

SSH dans le droplet :

```bash
ssh root@<DROPLET-IP>
```

### 1a. Installer Docker

```bash
curl -fsSL https://get.docker.com | sh
```

Vérifier :

```bash
docker --version
docker compose version
```

### 1b. Créer un swap de 2 Go (CRUCIAL avec 1 Go de RAM)

Le build Vite de `doctor-web` consomme jusqu'à 1.2 Go de RAM. Sans swap, le droplet OOM-killera npm pendant le `npm run build`.

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
free -h   # Confirmer : Swap ≈ 2.0Gi
```

### 1c. Cloner le repo

```bash
cd /opt
git clone git@gitlab.unige.ch:Filipe.Ramos/yalla.git
# OU avec HTTPS si la clé SSH n'est pas configurée :
# git clone https://gitlab.unige.ch/Filipe.Ramos/yalla.git
cd yalla
git checkout develop
```

### 1d. Configurer l'environnement

```bash
cp .env.production.example .env
nano .env   # remplir TOUS les champs marqués REQUIRED
```

Variables critiques à set :

- `DEPLOY_HOST` — par exemple `<droplet-ip-avec-tirets>.nip.io` (gratuit, mappe automatiquement à ton IP, Let's Encrypt fonctionne).
- `SUPABASE_URL`, `SUPABASE_KEY` — depuis ton projet Supabase prod.
- `API_SECRET_TOKEN` — généré via `openssl rand -base64 48 | tr -d /+= | head -c 48`.
- `CORS_ORIGINS`, `FRONTEND_BASE_URL`, `VITE_API_BASE_URL` — tous égaux à `https://<DEPLOY_HOST>`.
- `LETSENCRYPT_EMAIL` — pour les renouvellements de certificat.

### 1e. Ouvrir les ports

DO firewall (depuis le dashboard) ou via UFW :

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

## 2. Premier déploiement

```bash
cd /opt/yalla
docker compose up -d --build
```

Le `--build` lance la construction des deux images. **Attendre ~5 à 10 minutes** la première fois (Vite + npm install dans le doctor-web, image Python pour le backend).

Suivre les logs :

```bash
docker compose logs -f
```

À l'apparition de :

- `backend: Application startup complete.`
- `caddy: [INFO] cert obtained ...`
- `doctor-web: Configuration complete; ready for start up`

… c'est en l'air. Ouvre `https://<DEPLOY_HOST>` dans un navigateur.

## 3. Vérifications post-deploy

| URL | Attendu |
|---|---|
| `https://<host>/` | Écran de login doctor-web |
| `https://<host>/docs` | Swagger UI FastAPI |
| `https://<host>/api/doctors/me` avec `Authorization: Bearer <API_SECRET_TOKEN>` | JSON du Dr. Nadia Benali (legacy demo) |

Test rapide depuis ton laptop :

```bash
curl https://<host>/
curl -H "Authorization: Bearer <API_SECRET_TOKEN>" https://<host>/api/doctors/me
```

## 4. Mises à jour suivantes

```bash
cd /opt/yalla
git pull origin develop
docker compose up -d --build
```

Le `--build` rebuilt les images qui ont changé (Docker cache le reste).

Pour redémarrer un seul service :

```bash
docker compose restart backend
docker compose restart doctor-web
```

## 5. Diagnostic / dépannage

### Caddy n'arrive pas à obtenir le certificat

- Les ports 80 et 443 sont-ils ouverts ? `ufw status` et le DO firewall.
- Le DNS pointe-t-il vraiment vers ton droplet ? `dig <DEPLOY_HOST>` doit renvoyer l'IP du droplet.
- Lien de debug Caddy : `docker compose logs caddy | grep -i acme`.

### Le backend redémarre en boucle (OOM)

```bash
docker compose ps
docker compose logs backend --tail=50
```

Si OOM-kill : vérifier que le swap est bien actif (`free -h`). Sinon redémarrer le swap (`swapon /swapfile`).

### Vite build échoue (OOM)

Idem : le swap est-il actif ? Sinon build l'image en local puis push à un registry, voir « Alternative : build local + registry » plus bas.

### CORS errors dans le navigateur

`CORS_ORIGINS` dans `.env` doit inclure exactement le scheme + host (`https://yalla.example.com`, pas `yalla.example.com`). Modifier puis `docker compose restart backend`.

### Sessions de patient ne se créent pas

Les migrations Supabase 001 à 012 sont-elles appliquées en prod ? Voir issue #31. Surtout 004 (auth_user_id), 007 (account_setup_tokens), 011 (messaging), 012 (storage bucket).

## Alternative : build local + registry (si le droplet OOM toujours)

1. Sur le laptop, build les images locales :

   ```bash
   docker build -t registry.digitalocean.com/<your-registry>/yalla-backend .
   docker build -t registry.digitalocean.com/<your-registry>/yalla-doctor-web ./frontend/doctor-web --build-arg VITE_API_BASE_URL=https://<host>
   ```

2. Push :

   ```bash
   docker push registry.digitalocean.com/<your-registry>/yalla-backend
   docker push registry.digitalocean.com/<your-registry>/yalla-doctor-web
   ```

3. Sur le droplet, modifier `docker-compose.yml` pour remplacer les `build:` par `image: registry.digitalocean.com/<your-registry>/...`, puis `docker compose pull && docker compose up -d`.

## Coût récapitulatif

- Droplet `s-1vcpu-1gb` Amsterdam : **~6CHF/mois**
- Supabase free tier : **0 €** (suffit pour < 50k requêtes / mois en démo)
- DNS `nip.io` : **0 €**
- Domaine custom (optionnel) : ~10 CHF/an
- TheFork API : **0 CHF** (partenariat) 

**Total : ~ 6CHF/mois.**
