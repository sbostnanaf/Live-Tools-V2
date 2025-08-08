# 📊 Trading Dashboard - Professional Bot Monitoring Platform

Une application web moderne et sécurisée pour le suivi en temps réel de vos bots de trading. Interface professionnelle avec thème sombre, analytics avancées et déploiement prêt pour la production sur AWS.

![Trading Dashboard](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Docker](https://img.shields.io/badge/Docker-Enabled-blue)
![Security](https://img.shields.io/badge/Security-Enterprise%20Grade-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🌟 Fonctionnalités

### 📈 Dashboard Principal
- **Suivi du Capital** : Évolution horaire en temps réel
- **Métriques Clés** : Capital initial/actuel, variation absolue et pourcentage
- **Graphiques Interactifs** : Charts avec zoom et détails au survol
- **Multi-périodes** : 24h, 7j, 30j, depuis le début

### 💰 Analyse P&L (Profit & Loss)
- **Par Crypto** : Gains/pertes détaillés par cryptomonnaie
- **Par Trade** : Liste complète des trades avec détails
- **Agrégations Temporelles** : P&L journalier, mensuel, total
- **Métriques de Performance** : Win rate, profit/perte moyenne, ratio risque/rendement

### 🔐 Sécurité Enterprise
- **Authentification JWT** : Tokens sécurisés avec refresh automatique
- **Chiffrement** : Toutes les données sensibles chiffrées
- **Rate Limiting** : Protection contre les attaques par déni de service
- **HTTPS Obligatoire** : SSL/TLS avec certificats Let's Encrypt
- **Headers de Sécurité** : CSP, HSTS, X-Frame-Options, etc.

### 🎨 Interface Moderne
- **Thème Sombre** : Design professionnel adapté aux plateformes financières
- **Responsive** : Compatible desktop, tablette et mobile
- **Temps Réel** : Mise à jour automatique des données
- **Animations** : Transitions fluides et indicateurs visuels

### 📊 Monitoring et Analytics
- **Système de Monitoring** : Prometheus + Grafana intégrés
- **Logs Centralisés** : Suivi complet des activités
- **Alertes** : Notifications en cas de problème
- **Métriques Système** : CPU, RAM, réseau, Docker containers

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     NGINX Reverse Proxy                     │
│                    (SSL/TLS + Security)                     │
└─────────────────┬─────────────────┬─────────────────────────┘
                  │                 │
         ┌────────▼────────┐       ┌▼─────────────────┐
         │  React Frontend │       │  FastAPI Backend │
         │  (Port 3000)    │       │   (Port 8000)    │
         └─────────────────┘       └┬─────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
       ┌────▼─────┐           ┌─────▼─────┐         ┌──────▼──────┐
       │PostgreSQL│           │   Redis   │         │ Monitoring  │
       │   DB     │           │   Cache   │         │(Prometheus) │
       └──────────┘           └───────────┘         └─────────────┘
```

### Stack Technique

#### Backend
- **FastAPI** : API REST haute performance avec validation automatique
- **PostgreSQL** : Base de données relationnelle avec indexes optimisés
- **Redis** : Cache en mémoire pour les performances
- **SQLAlchemy** : ORM async pour les requêtes complexes
- **Alembic** : Migrations de base de données
- **JWT** : Authentification sécurisée
- **Prometheus** : Métriques et monitoring

#### Frontend
- **React 18** : Interface utilisateur moderne avec hooks
- **TypeScript** : Développement type-safe
- **Tailwind CSS** : Framework CSS utilitaire avec thème custom
- **Recharts** : Graphiques interactifs pour les données financières
- **React Query** : Gestion d'état et cache côté client
- **Framer Motion** : Animations fluides

#### Infrastructure
- **Docker Compose** : Orchestration multi-conteneurs
- **Nginx** : Reverse proxy avec SSL/TLS et sécurité
- **Let's Encrypt** : Certificats SSL gratuits et automatiques
- **Grafana** : Dashboards de monitoring
- **UFW** : Firewall système

## 🚀 Installation Rapide

### Prérequis
- **AWS EC2** : Instance t3.medium minimum (2 vCPU, 4 GB RAM)
- **Système** : Ubuntu 20.04+ ou Amazon Linux 2
- **Stockage** : 20 GB SSD minimum
- **Réseau** : Ports 22 (SSH), 80 (HTTP), 443 (HTTPS) ouverts

### Déploiement Automatique

```bash
# 1. Cloner le repository
git clone <your-repository-url>
cd trading-dashboard

# 2. Rendre le script exécutable
chmod +x deploy/aws-deploy.sh

# 3. Lancer le déploiement automatique
./deploy/aws-deploy.sh
```

Le script automatique va :
- ✅ Installer toutes les dépendances (Docker, Docker Compose, etc.)
- ✅ Configurer le firewall (UFW)
- ✅ Générer les certificats SSL
- ✅ Configurer les variables d'environnement
- ✅ Déployer tous les services
- ✅ Configurer le monitoring et les sauvegardes
- ✅ Optionnel : Configurer Let's Encrypt

### Configuration Manuelle (Avancée)

<details>
<summary>Cliquez pour voir les étapes manuelles</summary>

#### 1. Cloner et Configurer

```bash
git clone <your-repository-url>
cd trading-dashboard

# Copier et configurer l'environnement
cp .env.example .env
nano .env  # Éditer les variables d'environnement
```

#### 2. Configuration SSL

```bash
# Générer certificats auto-signés pour le test
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/trading-dashboard.key \
    -out nginx/ssl/trading-dashboard.crt \
    -subj "/C=US/ST=State/L=City/O=TradingDashboard/CN=your-domain.com"
```

#### 3. Déploiement

```bash
# Construire et démarrer
docker-compose build
docker-compose up -d

# Vérifier le statut
docker-compose ps
docker-compose logs -f
```

</details>

## 🔧 Configuration

### Variables d'Environnement

Copiez `.env.example` vers `.env` et configurez :

```bash
# Base de données
POSTGRES_DB=trading_db
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=votre_mot_de_passe_securise

# Redis
REDIS_PASSWORD=votre_mot_de_passe_redis

# JWT
JWT_SECRET_KEY=votre_cle_secrete_jwt_minimum_32_caracteres

# Domaine
DOMAIN_NAME=votre-domaine.com
REACT_APP_API_URL=https://votre-domaine.com/api

# Integration Trading Bot
AWS_TRADING_BOT_URL=http://votre-instance-ip:8001
AWS_TRADING_BOT_API_KEY=votre_cle_api_bot

# Monitoring
GRAFANA_PASSWORD=votre_mot_de_passe_grafana

# Let's Encrypt
LETSENCRYPT_EMAIL=votre-email@domaine.com
```

### Configuration AWS EC2

#### Security Groups
```
Type        Protocol    Port    Source
SSH         TCP         22      Votre IP
HTTP        TCP         80      0.0.0.0/0
HTTPS       TCP         443     0.0.0.0/0
```

#### Instance Recommandée
- **Type** : t3.medium (2 vCPU, 4 GB RAM)
- **Stockage** : 20 GB GP3 SSD
- **OS** : Ubuntu 20.04 LTS
- **Elastic IP** : Recommandé pour un domaine fixe

## 🔗 Intégration Trading Bot

### API Integration

Le dashboard se connecte à votre bot de trading via API REST :

```python
# Example d'intégration dans votre bot
import requests

API_URL = "https://votre-dashboard.com/api"
API_KEY = "votre_cle_api"

# Envoyer les données de trade
trade_data = {
    "symbol": "BTCUSDT",
    "type": "long",
    "entry_price": 45000.0,
    "quantity": 0.1,
    "timestamp": "2024-01-01T10:00:00Z"
}

response = requests.post(
    f"{API_URL}/trading/trades",
    json=trade_data,
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

### Webhooks (Optionnel)

Configurez des webhooks pour recevoir les données en temps réel :

```bash
curl -X POST "https://votre-dashboard.com/api/webhooks/trade" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "trade_closed",
    "symbol": "ETHUSDT",
    "pnl": 150.25,
    "timestamp": "2024-01-01T10:30:00Z"
  }'
```

## 📚 Utilisation

### Accès au Dashboard

1. **Ouverture** : https://votre-domaine.com ou https://votre-ip-publique
2. **Connexion** : Utilisez vos identifiants configurés
3. **Navigation** : Interface intuitive avec menu latéral

### Principales Sections

#### 📊 Dashboard Principal
- Vue d'ensemble du capital et des performances
- Graphiques en temps réel des évolutions
- Métriques clés et indicateurs de performance

#### 💱 Trading
- Liste détaillée de tous les trades
- Filtres par date, symbole, stratégie
- Export des données (CSV, PDF)

#### 📈 Analytics
- Analyses approfondies des performances
- Comparaison avec les benchmarks (BTC, ETH)
- Calculs de drawdown et volatilité

#### ⚙️ Settings
- Configuration des paramètres d'affichage
- Gestion des comptes de trading
- Paramètres de sécurité

### Monitoring

#### Grafana Dashboard
Accédez à : `https://votre-domaine.com:3001`
- Username : admin
- Password : (défini dans .env)

#### Métriques Disponibles
- Performances système (CPU, RAM, disque)
- Statistiques des conteneurs Docker
- Métriques applicatives (requêtes API, temps de réponse)
- Alertes personnalisables

## 🛠️ Maintenance

### Mise à Jour

```bash
# Script automatique de mise à jour
./scripts/update.sh
```

Le script de mise à jour :
- ✅ Crée une sauvegarde automatique
- ✅ Met à jour le code et les images Docker
- ✅ Exécute les migrations de base de données
- ✅ Redémarre les services sans interruption
- ✅ Vérifie la santé des services
- ✅ Rollback automatique en cas d'échec

### Sauvegarde

```bash
# Sauvegarde manuelle
./scripts/backup.sh

# Les sauvegardes automatiques sont configurées quotidiennement
```

### Surveillance des Logs

```bash
# Logs en temps réel
docker-compose logs -f

# Logs spécifiques
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f nginx
```

### Commandes Utiles

```bash
# Redémarrer tous les services
docker-compose restart

# Redémarrer un service spécifique
docker-compose restart backend

# Voir l'état des services
docker-compose ps

# Accéder au shell d'un conteneur
docker-compose exec backend bash
docker-compose exec postgres psql -U trading_user -d trading_db

# Vérifier l'utilisation des ressources
docker stats

# Nettoyer les images inutilisées
docker system prune -a
```

## 🔒 Sécurité

### Mesures de Sécurité Implémentées

- **Authentification JWT** avec refresh tokens
- **Chiffrement HTTPS** obligatoire (TLS 1.2+)
- **Rate Limiting** sur toutes les APIs
- **Headers de sécurité** (HSTS, CSP, etc.)
- **Validation des entrées** côté backend
- **Audit Trail** complet des actions utilisateur
- **Isolation des conteneurs** Docker
- **Firewall UFW** configuré automatiquement

### Bonnes Pratiques

1. **Mots de passe** : Utilisez des mots de passe forts (générés automatiquement)
2. **SSH** : Désactivez l'authentification par mot de passe
3. **Updates** : Maintenez le système et Docker à jour
4. **Monitoring** : Surveillez les logs pour détecter les intrusions
5. **Backups** : Vérifiez régulièrement les sauvegardes
6. **SSL** : Renouvelez les certificats Let's Encrypt automatiquement

## 🆘 Dépannage

### Problèmes Courants

<details>
<summary>Service ne démarre pas</summary>

```bash
# Vérifier les logs
docker-compose logs nom_du_service

# Reconstruire le conteneur
docker-compose build --no-cache nom_du_service
docker-compose up -d nom_du_service
```
</details>

<details>
<summary>Erreur de base de données</summary>

```bash
# Vérifier la connexion PostgreSQL
docker-compose exec postgres pg_isready -U trading_user

# Vérifier l'espace disque
df -h

# Redémarrer PostgreSQL
docker-compose restart postgres
```
</details>

<details>
<summary>Problème SSL</summary>

```bash
# Vérifier les certificats
openssl x509 -in nginx/ssl/trading-dashboard.crt -text -noout

# Renouveler Let's Encrypt
sudo certbot renew --dry-run
```
</details>

<details>
<summary>Performance lente</summary>

```bash
# Vérifier l'utilisation des ressources
docker stats
htop

# Analyser les logs de performance
docker-compose logs nginx | grep "response_time"
```
</details>

### Support et Contact

Pour le support technique :
1. Consultez les logs : `docker-compose logs -f`
2. Vérifiez les métriques Grafana
3. Consultez la documentation des erreurs
4. Créez une issue avec les détails complets

## 📝 Changelog

### Version 1.0.0 (2024-01-01)
- 🎉 Version initiale
- ✅ Dashboard complet avec analytics
- ✅ Authentification sécurisée
- ✅ Déploiement automatique AWS
- ✅ Monitoring intégré
- ✅ Support SSL/TLS

## 📄 License

MIT License - voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

**🚀 Prêt pour la production | 🔒 Sécurité enterprise | 📊 Analytics professionnelles**

Made with ❤️ for professional traders