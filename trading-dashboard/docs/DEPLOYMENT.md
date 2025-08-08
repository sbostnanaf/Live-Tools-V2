# 🚀 Guide de Déploiement AWS - Trading Dashboard

Ce guide détaille le processus complet de déploiement de votre dashboard de trading sur AWS EC2.

## 📋 Table des Matières

1. [Prérequis AWS](#prérequis-aws)
2. [Configuration EC2](#configuration-ec2)
3. [Déploiement Automatique](#déploiement-automatique)
4. [Configuration DNS](#configuration-dns)
5. [SSL/TLS Setup](#ssltls-setup)
6. [Monitoring Setup](#monitoring-setup)
7. [Sécurité](#sécurité)
8. [Dépannage](#dépannage)

## 🎯 Prérequis AWS

### Compte AWS
- Compte AWS actif avec permissions EC2
- Elastic IP disponible (recommandé)
- Accès à Route 53 si vous utilisez un domaine personnalisé

### Instance EC2 Recommandée

| Composant | Minimum | Recommandé | Production |
|-----------|---------|------------|-------------|
| Type | t3.small | t3.medium | t3.large |
| vCPUs | 2 | 2 | 2 |
| RAM | 2 GB | 4 GB | 8 GB |
| Stockage | 15 GB | 20 GB | 50 GB |
| Réseau | Basic | Enhanced | Enhanced |

### AMI Recommandées
- **Ubuntu 20.04 LTS** (ami-0c02fb55956c7d316)
- **Ubuntu 22.04 LTS** (ami-08d4ac5b634553e16)
- **Amazon Linux 2** (ami-0abcdef1234567890)

## 🖥️ Configuration EC2

### 1. Lancement de l'Instance

```bash
# Via AWS CLI
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t3.medium \
    --key-name votre-cle-ssh \
    --security-group-ids sg-xxxxxxxxx \
    --subnet-id subnet-xxxxxxxxx \
    --associate-public-ip-address \
    --block-device-mappings '[{
        "DeviceName": "/dev/sda1",
        "Ebs": {
            "VolumeSize": 20,
            "VolumeType": "gp3",
            "DeleteOnTermination": true
        }
    }]' \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=TradingDashboard}]'
```

### 2. Security Group

Créez un Security Group avec les règles suivantes :

| Type | Protocol | Port | Source | Description |
|------|----------|------|---------|-------------|
| SSH | TCP | 22 | Votre IP | Accès administrateur |
| HTTP | TCP | 80 | 0.0.0.0/0 | Trafic web |
| HTTPS | TCP | 443 | 0.0.0.0/0 | Trafic web sécurisé |
| Custom TCP | TCP | 3001 | Votre IP | Grafana (optionnel) |

```bash
# Créer le Security Group
aws ec2 create-security-group \
    --group-name trading-dashboard-sg \
    --description "Security group for Trading Dashboard"

# Ajouter les règles
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol tcp \
    --port 22 \
    --source-group 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol tcp \
    --port 80 \
    --source-group 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol tcp \
    --port 443 \
    --source-group 0.0.0.0/0
```

### 3. Elastic IP (Recommandé)

```bash
# Allouer une Elastic IP
aws ec2 allocate-address --domain vpc

# Associer à l'instance
aws ec2 associate-address \
    --instance-id i-xxxxxxxxx \
    --allocation-id eipalloc-xxxxxxxxx
```

## 🚀 Déploiement Automatique

### 1. Connexion à l'Instance

```bash
# Connexion SSH
ssh -i votre-cle.pem ubuntu@votre-ip-publique

# Ou utilisez votre configuration SSH existante
ssh SERVEUR_NANAF
```

### 2. Script de Déploiement Automatique

```bash
# Cloner le repository
git clone https://github.com/votre-username/trading-dashboard.git
cd trading-dashboard

# Rendre le script exécutable
chmod +x deploy/aws-deploy.sh

# Lancer le déploiement
./deploy/aws-deploy.sh
```

### 3. Processus de Déploiement

Le script automatique effectue les étapes suivantes :

#### Phase 1 : Préparation du Système
```bash
[INFO] Checking system requirements...
[INFO] Installing system dependencies...
[SUCCESS] Docker installed
[SUCCESS] Docker Compose installed
```

#### Phase 2 : Configuration Sécurité
```bash
[INFO] Configuring firewall...
[SUCCESS] Firewall configured
[INFO] Setting up SSL certificates...
[SUCCESS] Self-signed SSL certificates generated
```

#### Phase 3 : Configuration Application
```bash
[INFO] Setting up environment variables...
[SUCCESS] Generated random database password
[SUCCESS] Generated random Redis password
[SUCCESS] Generated random JWT secret
[SUCCESS] Environment variables configured
```

#### Phase 4 : Déploiement
```bash
[INFO] Building and deploying the application...
[SUCCESS] postgres is running
[SUCCESS] redis is running
[SUCCESS] backend is running
[SUCCESS] frontend is running
[SUCCESS] nginx is running
[SUCCESS] Application deployed successfully
```

### 4. Configuration Post-Déploiement

Après le déploiement automatique :

```bash
# Vérifier l'état des services
docker-compose ps

# Vérifier les logs
docker-compose logs -f

# Test de connectivité
curl -k https://localhost/health
```

## 🌐 Configuration DNS

### Option 1 : Route 53 (AWS)

```bash
# Créer une Hosted Zone
aws route53 create-hosted-zone \
    --name votre-domaine.com \
    --caller-reference $(date +%s)

# Créer un enregistrement A
aws route53 change-resource-record-sets \
    --hosted-zone-id Z123456789 \
    --change-batch '{
        "Changes": [{
            "Action": "CREATE",
            "ResourceRecordSet": {
                "Name": "dashboard.votre-domaine.com",
                "Type": "A",
                "TTL": 300,
                "ResourceRecords": [{"Value": "VOTRE-IP-PUBLIQUE"}]
            }
        }]
    }'
```

### Option 2 : Registrar Externe

Chez votre registrar de domaine, créez :
- **Enregistrement A** : `dashboard.votre-domaine.com` → `VOTRE-IP-PUBLIQUE`
- **TTL** : 300 secondes (5 minutes)

### Vérification DNS

```bash
# Vérifier la propagation DNS
nslookup dashboard.votre-domaine.com
dig dashboard.votre-domaine.com

# Test depuis différents serveurs DNS
dig @8.8.8.8 dashboard.votre-domaine.com
dig @1.1.1.1 dashboard.votre-domaine.com
```

## 🔒 SSL/TLS Setup

### Option 1 : Let's Encrypt (Recommandé)

Le script de déploiement propose automatiquement Let's Encrypt :

```bash
# Pendant le déploiement
Do you want to set up Let's Encrypt SSL certificates? (y/n): y
Enter your domain name: dashboard.votre-domaine.com
Enter your email address: admin@votre-domaine.com

[INFO] Setting up Let's Encrypt for dashboard.votre-domaine.com...
[SUCCESS] Let's Encrypt SSL certificates configured
```

### Option 2 : Configuration Manuelle Let's Encrypt

```bash
# Installer Certbot
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Obtenir le certificat
sudo certbot --nginx -d dashboard.votre-domaine.com \
    --email admin@votre-domaine.com \
    --agree-tos \
    --non-interactive

# Vérifier le renouvellement automatique
sudo certbot renew --dry-run

# Configurer le renouvellement automatique
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### Option 3 : Certificat Personnalisé

```bash
# Copier vos certificats
sudo cp votre-certificat.crt /opt/trading-dashboard/nginx/ssl/
sudo cp votre-cle-privee.key /opt/trading-dashboard/nginx/ssl/

# Modifier la configuration Nginx
sudo nano /opt/trading-dashboard/nginx/nginx.conf

# Redémarrer Nginx
docker-compose restart nginx
```

### Vérification SSL

```bash
# Test SSL
openssl s_client -connect dashboard.votre-domaine.com:443 -servername dashboard.votre-domaine.com

# Vérification en ligne
curl -I https://dashboard.votre-domaine.com/health

# Test de sécurité SSL
# Utilisez https://www.ssllabs.com/ssltest/
```

## 📊 Monitoring Setup

### Grafana Configuration

```bash
# Accéder à Grafana
https://dashboard.votre-domaine.com:3001

# Identifiants par défaut
Username: admin
Password: (défini dans .env GRAFANA_PASSWORD)
```

### Dashboards Prédéfinis

1. **System Metrics**
   - CPU, RAM, Disk utilization
   - Network traffic
   - Docker container status

2. **Application Metrics**
   - API response times
   - Database queries
   - Active users
   - Trade volume

3. **Security Metrics**
   - Failed login attempts
   - API rate limiting
   - Error rates

### Prometheus Targets

Le fichier `monitoring/prometheus.yml` configure automatiquement :

```yaml
scrape_configs:
  - job_name: 'trading-dashboard'
    static_configs:
      - targets: ['backend:8000']
  
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
  
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:8080']
```

### Alertes Personnalisées

```bash
# Éditer les règles d'alerte
nano monitoring/alert-rules.yml

# Exemple d'alerte
groups:
  - name: trading-dashboard-alerts
    rules:
      - alert: HighCPUUsage
        expr: cpu_usage_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% for more than 5 minutes"
```

## 🛡️ Sécurité

### Hardening du Système

```bash
# Mise à jour du système
sudo apt update && sudo apt upgrade -y

# Configuration SSH sécurisée
sudo nano /etc/ssh/sshd_config

# Ajouts recommandés :
# PasswordAuthentication no
# PermitRootLogin no
# Protocol 2
# AllowUsers ubuntu

# Redémarrer SSH
sudo systemctl restart ssh

# Installation fail2ban
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Configuration UFW Avancée

```bash
# Règles spécifiques par IP (optionnel)
sudo ufw allow from VOTRE_IP_BUREAU to any port 3001  # Grafana
sudo ufw allow from VOTRE_IP_BUREAU to any port 9090  # Prometheus

# Limitation de débit SSH
sudo ufw limit ssh

# Log UFW
sudo ufw logging on

# Vérifier les règles
sudo ufw status verbose
```

### Monitoring Sécurité

```bash
# Logs de sécurité
sudo tail -f /var/log/auth.log
sudo tail -f /var/log/ufw.log

# Surveillance des connexions
sudo netstat -tulnp | grep :443
sudo ss -tulnp | grep :443

# Vérification des processus Docker
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## 🔧 Optimisation Performance

### Configuration Docker

```bash
# Optimisation Docker daemon
sudo nano /etc/docker/daemon.json

{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "name": "nofile",
      "hard": 64000,
      "soft": 64000
    }
  }
}

# Redémarrer Docker
sudo systemctl restart docker
```

### Optimisation Nginx

```bash
# Ajustements de performance dans nginx.conf
worker_processes auto;
worker_connections 2048;
client_max_body_size 16M;

# Cache statique
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header Vary "Accept-Encoding";
}
```

### Optimisation PostgreSQL

```bash
# Configuration PostgreSQL
docker-compose exec postgres bash -c "echo '
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
' >> /var/lib/postgresql/data/postgresql.conf"

# Redémarrer PostgreSQL
docker-compose restart postgres
```

## 🔍 Dépannage

### Problèmes de Déploiement

#### Erreur : Port déjà utilisé
```bash
# Identifier le processus utilisant le port
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :443

# Arrêter le processus conflictuel
sudo systemctl stop apache2  # Si Apache est installé
sudo systemctl stop nginx    # Si Nginx système est installé

# Redéployer
docker-compose up -d
```

#### Erreur : Espace disque insuffisant
```bash
# Vérifier l'espace disque
df -h

# Nettoyer Docker
docker system prune -a
docker volume prune

# Nettoyer les logs système
sudo journalctl --vacuum-time=7d
```

#### Erreur : Mémoire insuffisante
```bash
# Vérifier l'utilisation mémoire
free -h
docker stats

# Ajouter du swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Problèmes SSL

#### Certificat Let's Encrypt échoue
```bash
# Vérifier la configuration DNS
nslookup votre-domaine.com

# Vérifier l'accessibilité du serveur
curl -I http://votre-domaine.com/.well-known/acme-challenge/

# Renouveler manuellement
sudo certbot renew --force-renewal -d votre-domaine.com
```

#### Erreur de certificat auto-signé
```bash
# Régénérer les certificats
rm -f nginx/ssl/*
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/trading-dashboard.key \
    -out nginx/ssl/trading-dashboard.crt \
    -subj "/C=FR/ST=State/L=City/O=TradingDashboard/CN=votre-domaine.com"

# Redémarrer Nginx
docker-compose restart nginx
```

### Problèmes de Performance

#### Application lente
```bash
# Vérifier les métriques système
htop
docker stats

# Analyser les logs Nginx
docker-compose logs nginx | grep "request_time"

# Vérifier la base de données
docker-compose exec postgres pg_stat_activity

# Optimiser les requêtes lentes
docker-compose exec postgres psql -U trading_user -d trading_db \
    -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

### Support et Logs

#### Collecte d'Informations de Debug
```bash
# Script de diagnostic complet
cat > debug-info.sh << 'EOF'
#!/bin/bash
echo "=== System Information ==="
uname -a
df -h
free -h
docker --version
docker-compose --version

echo -e "\n=== Docker Status ==="
docker-compose ps

echo -e "\n=== Service Logs (last 50 lines) ==="
docker-compose logs --tail=50

echo -e "\n=== Network Configuration ==="
ip addr show
ss -tulnp | grep -E ':(80|443|8000|3000|5432|6379)'

echo -e "\n=== Nginx Configuration Test ==="
docker-compose exec nginx nginx -t 2>&1 || echo "Nginx config test failed"

echo -e "\n=== SSL Certificate Info ==="
openssl x509 -in nginx/ssl/trading-dashboard.crt -text -noout | grep -E "(Subject|Not After)" 2>/dev/null || echo "SSL certificate not found"
EOF

chmod +x debug-info.sh
./debug-info.sh > diagnostic-report.txt
```

## 📞 Support

Pour obtenir de l'aide :

1. **Logs détaillés** : `docker-compose logs -f`
2. **État des services** : `docker-compose ps`
3. **Métriques système** : Grafana dashboard
4. **Documentation** : Consultez les fichiers de docs/
5. **Issues** : Créez une issue avec le rapport de diagnostic

---

**Déploiement réussi ?** 🎉 Votre dashboard est maintenant accessible à `https://votre-domaine.com` !