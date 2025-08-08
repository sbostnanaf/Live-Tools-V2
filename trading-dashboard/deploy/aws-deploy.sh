#!/bin/bash

# Trading Dashboard AWS Deployment Script
# This script automates the deployment of the trading dashboard on AWS EC2

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="trading-dashboard"
DOCKER_COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root"
        exit 1
    fi
}

# Check system requirements
check_requirements() {
    print_status "Checking system requirements..."
    
    # Check for required commands
    local required_commands=("docker" "docker-compose" "git" "curl" "openssl")
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            print_error "$cmd is not installed"
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    
    print_success "All requirements met"
}

# Install system dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    
    # Update package list
    sudo apt update
    
    # Install required packages
    sudo apt install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        git \
        htop \
        vim \
        ufw
    
    # Install Docker if not present
    if ! command -v docker &> /dev/null; then
        print_status "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        print_success "Docker installed"
    fi
    
    # Install Docker Compose if not present
    if ! command -v docker-compose &> /dev/null; then
        print_status "Installing Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        print_success "Docker Compose installed"
    fi
    
    print_success "Dependencies installed"
}

# Configure firewall
setup_firewall() {
    print_status "Configuring firewall..."
    
    # Enable UFW
    sudo ufw --force enable
    
    # Default policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Allow SSH (be careful!)
    sudo ufw allow ssh
    
    # Allow HTTP and HTTPS
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    
    # Allow specific ports if needed
    sudo ufw allow 22/tcp
    
    print_success "Firewall configured"
}

# Create application directory structure
setup_directories() {
    print_status "Setting up directory structure..."
    
    local app_dir="/opt/$PROJECT_NAME"
    local backup_dir="/opt/$PROJECT_NAME/backups"
    local logs_dir="/opt/$PROJECT_NAME/logs"
    
    # Create directories
    sudo mkdir -p "$app_dir" "$backup_dir" "$logs_dir"
    sudo chown -R $USER:$USER "$app_dir"
    
    # Set permissions
    chmod 755 "$app_dir"
    chmod 755 "$backup_dir"
    chmod 755 "$logs_dir"
    
    print_success "Directory structure created"
}

# Generate SSL certificates
setup_ssl() {
    print_status "Setting up SSL certificates..."
    
    local ssl_dir="./nginx/ssl"
    mkdir -p "$ssl_dir"
    
    # Check if certificates already exist
    if [[ -f "$ssl_dir/trading-dashboard.crt" && -f "$ssl_dir/trading-dashboard.key" ]]; then
        print_warning "SSL certificates already exist, skipping generation"
        return
    fi
    
    # Generate self-signed certificate for initial setup
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$ssl_dir/trading-dashboard.key" \
        -out "$ssl_dir/trading-dashboard.crt" \
        -subj "/C=US/ST=State/L=City/O=TradingDashboard/CN=localhost"
    
    print_success "Self-signed SSL certificates generated"
    print_warning "Remember to replace with proper SSL certificates for production"
}

# Setup Let's Encrypt (optional)
setup_letsencrypt() {
    read -p "Do you want to set up Let's Encrypt SSL certificates? (y/n): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        return
    fi
    
    read -p "Enter your domain name: " domain_name
    read -p "Enter your email address: " email_address
    
    if [[ -z "$domain_name" || -z "$email_address" ]]; then
        print_error "Domain name and email are required for Let's Encrypt"
        return
    fi
    
    print_status "Setting up Let's Encrypt for $domain_name..."
    
    # Install certbot
    sudo apt install -y certbot python3-certbot-nginx
    
    # Get certificate
    sudo certbot --nginx -d "$domain_name" --email "$email_address" --agree-tos --non-interactive
    
    # Set up auto-renewal
    echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
    
    print_success "Let's Encrypt SSL certificates configured"
}

# Configure environment variables
setup_environment() {
    print_status "Setting up environment variables..."
    
    if [[ ! -f "$ENV_FILE" ]]; then
        # Copy from example
        if [[ -f ".env.example" ]]; then
            cp .env.example "$ENV_FILE"
            print_success "Environment file created from example"
        else
            print_error ".env.example file not found"
            exit 1
        fi
    fi
    
    print_warning "Please review and update the environment variables in $ENV_FILE"
    
    # Generate random secrets if they're still default
    if grep -q "YOUR_SECURE_DB_PASSWORD_HERE" "$ENV_FILE"; then
        local db_password=$(openssl rand -base64 32)
        sed -i "s/YOUR_SECURE_DB_PASSWORD_HERE/$db_password/g" "$ENV_FILE"
        print_success "Generated random database password"
    fi
    
    if grep -q "YOUR_SECURE_REDIS_PASSWORD_HERE" "$ENV_FILE"; then
        local redis_password=$(openssl rand -base64 32)
        sed -i "s/YOUR_SECURE_REDIS_PASSWORD_HERE/$redis_password/g" "$ENV_FILE"
        print_success "Generated random Redis password"
    fi
    
    if grep -q "YOUR_SUPER_SECRET_JWT_KEY_MINIMUM_32_CHARACTERS_HERE" "$ENV_FILE"; then
        local jwt_secret=$(openssl rand -base64 64)
        sed -i "s/YOUR_SUPER_SECRET_JWT_KEY_MINIMUM_32_CHARACTERS_HERE/$jwt_secret/g" "$ENV_FILE"
        print_success "Generated random JWT secret"
    fi
    
    if grep -q "YOUR_SECURE_GRAFANA_PASSWORD_HERE" "$ENV_FILE"; then
        local grafana_password=$(openssl rand -base64 16)
        sed -i "s/YOUR_SECURE_GRAFANA_PASSWORD_HERE/$grafana_password/g" "$ENV_FILE"
        print_success "Generated random Grafana password"
    fi
    
    print_success "Environment variables configured"
}

# Build and start the application
deploy_application() {
    print_status "Building and deploying the application..."
    
    # Pull latest images and build
    docker-compose pull
    docker-compose build --no-cache
    
    # Start services
    docker-compose up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    local services=("postgres" "redis" "backend" "frontend" "nginx")
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            print_success "$service is running"
        else
            print_error "$service failed to start"
            docker-compose logs "$service"
        fi
    done
    
    print_success "Application deployed successfully"
}

# Setup monitoring and logging
setup_monitoring() {
    print_status "Setting up monitoring and logging..."
    
    # Create log rotation configuration
    sudo tee /etc/logrotate.d/trading-dashboard > /dev/null <<EOF
/opt/trading-dashboard/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
}
EOF
    
    # Setup system monitoring script
    tee monitoring/system-monitor.sh > /dev/null <<'EOF'
#!/bin/bash
# System monitoring script

LOG_FILE="/opt/trading-dashboard/logs/system-monitor.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# System metrics
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2+$4}' | cut -d'%' -f1)
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')
DISK_USAGE=$(df -h / | awk 'NR==2{print $5}' | cut -d'%' -f1)

# Docker container status
CONTAINER_STATUS=$(docker-compose ps --services --filter "status=running" | wc -l)
TOTAL_CONTAINERS=$(docker-compose ps --services | wc -l)

# Log metrics
echo "[$TIMESTAMP] CPU: ${CPU_USAGE}% | Memory: ${MEMORY_USAGE}% | Disk: ${DISK_USAGE}% | Containers: ${CONTAINER_STATUS}/${TOTAL_CONTAINERS}" >> "$LOG_FILE"

# Alert if high resource usage
if (( $(echo "$CPU_USAGE > 80" | bc -l) )); then
    echo "[$TIMESTAMP] ALERT: High CPU usage: ${CPU_USAGE}%" >> "$LOG_FILE"
fi

if (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
    echo "[$TIMESTAMP] ALERT: High memory usage: ${MEMORY_USAGE}%" >> "$LOG_FILE"
fi

if [[ $DISK_USAGE -gt 80 ]]; then
    echo "[$TIMESTAMP] ALERT: High disk usage: ${DISK_USAGE}%" >> "$LOG_FILE"
fi
EOF
    
    chmod +x monitoring/system-monitor.sh
    
    # Setup cron job for monitoring
    (crontab -l 2>/dev/null; echo "*/5 * * * * /opt/trading-dashboard/monitoring/system-monitor.sh") | crontab -
    
    print_success "Monitoring and logging configured"
}

# Create backup script
setup_backup() {
    print_status "Setting up backup script..."
    
    tee scripts/backup.sh > /dev/null <<'EOF'
#!/bin/bash
# Backup script for trading dashboard

set -e

BACKUP_DIR="/opt/trading-dashboard/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="trading_dashboard_backup_$TIMESTAMP"

echo "Starting backup: $BACKUP_NAME"

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Backup database
docker-compose exec -T postgres pg_dumpall -U trading_user > "$BACKUP_DIR/$BACKUP_NAME/database.sql"

# Backup application data
tar -czf "$BACKUP_DIR/$BACKUP_NAME/app_data.tar.gz" \
    --exclude='*.log' \
    --exclude='node_modules' \
    --exclude='.git' \
    /opt/trading-dashboard

# Cleanup old backups (keep last 7 days)
find "$BACKUP_DIR" -type d -name "trading_dashboard_backup_*" -mtime +7 -exec rm -rf {} +

echo "Backup completed: $BACKUP_NAME"
EOF
    
    chmod +x scripts/backup.sh
    
    # Setup daily backup cron job
    (crontab -l 2>/dev/null; echo "0 2 * * * /opt/trading-dashboard/scripts/backup.sh >> /opt/trading-dashboard/logs/backup.log 2>&1") | crontab -
    
    print_success "Backup script configured"
}

# Display deployment information
show_info() {
    print_success "Deployment completed successfully!"
    echo
    print_status "Application Information:"
    echo "  - Application URL: https://$(curl -s ifconfig.me)"
    echo "  - Grafana Dashboard: https://$(curl -s ifconfig.me):3001"
    echo "  - Application Directory: /opt/$PROJECT_NAME"
    echo "  - Logs Directory: /opt/$PROJECT_NAME/logs"
    echo "  - Backups Directory: /opt/$PROJECT_NAME/backups"
    echo
    print_status "Useful Commands:"
    echo "  - View logs: docker-compose logs -f"
    echo "  - Restart services: docker-compose restart"
    echo "  - Update application: docker-compose pull && docker-compose up -d"
    echo "  - Backup data: ./scripts/backup.sh"
    echo
    print_warning "Next Steps:"
    echo "  1. Update DNS records to point to your server IP"
    echo "  2. Configure proper SSL certificates if using a custom domain"
    echo "  3. Review and update environment variables in $ENV_FILE"
    echo "  4. Set up monitoring alerts"
    echo "  5. Test all functionality"
}

# Main deployment function
main() {
    clear
    echo "=========================================="
    echo "  Trading Dashboard AWS Deployment"
    echo "=========================================="
    echo
    
    # Check if we're in the right directory
    if [[ ! -f "$DOCKER_COMPOSE_FILE" ]]; then
        print_error "docker-compose.yml not found. Please run this script from the project root directory."
        exit 1
    fi
    
    # Run deployment steps
    check_root
    check_requirements
    install_dependencies
    setup_firewall
    setup_directories
    setup_ssl
    setup_environment
    deploy_application
    setup_monitoring
    setup_backup
    setup_letsencrypt
    
    show_info
}

# Handle script interruption
trap 'print_error "Deployment interrupted"; exit 1' INT TERM

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi