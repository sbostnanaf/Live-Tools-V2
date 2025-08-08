#!/bin/bash

# Trading Dashboard Update Script
# This script handles safe updates of the trading dashboard application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Configuration
PROJECT_NAME="trading-dashboard"
BACKUP_DIR="/opt/$PROJECT_NAME/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup before update
create_backup() {
    print_status "Creating backup before update..."
    
    local backup_name="pre_update_backup_$TIMESTAMP"
    mkdir -p "$BACKUP_DIR/$backup_name"
    
    # Backup database
    docker-compose exec -T postgres pg_dumpall -U trading_user > "$BACKUP_DIR/$backup_name/database.sql"
    
    # Backup current application
    tar -czf "$BACKUP_DIR/$backup_name/app_data.tar.gz" \
        --exclude='*.log' \
        --exclude='node_modules' \
        --exclude='.git' \
        --exclude='backups' \
        .
    
    print_success "Backup created: $backup_name"
}

# Check if services are healthy before update
health_check() {
    print_status "Checking service health..."
    
    local services=("postgres" "redis" "backend" "frontend" "nginx")
    local unhealthy_services=()
    
    for service in "${services[@]}"; do
        if ! docker-compose ps "$service" | grep -q "Up"; then
            unhealthy_services+=("$service")
        fi
    done
    
    if [[ ${#unhealthy_services[@]} -gt 0 ]]; then
        print_warning "Unhealthy services detected: ${unhealthy_services[*]}"
        read -p "Continue with update? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Update cancelled by user"
            exit 1
        fi
    else
        print_success "All services are healthy"
    fi
}

# Pull latest changes from git
update_code() {
    print_status "Updating code from repository..."
    
    # Stash any local changes
    if ! git diff-index --quiet HEAD --; then
        print_warning "Local changes detected, stashing..."
        git stash push -m "Pre-update stash $TIMESTAMP"
    fi
    
    # Pull latest changes
    git pull origin main
    
    print_success "Code updated successfully"
}

# Update Docker images
update_images() {
    print_status "Updating Docker images..."
    
    # Pull latest base images
    docker-compose pull
    
    # Rebuild images with no cache
    docker-compose build --no-cache
    
    print_success "Docker images updated"
}

# Update database schema (migrations)
update_database() {
    print_status "Updating database schema..."
    
    # Run database migrations
    docker-compose exec backend python -c "
from alembic.config import Config
from alembic import command
import os

alembic_cfg = Config('/app/alembic.ini')
alembic_cfg.set_main_option('script_location', '/app/alembic')

try:
    command.upgrade(alembic_cfg, 'head')
    print('Database migrations completed successfully')
except Exception as e:
    print(f'Database migration failed: {e}')
    exit(1)
"
    
    print_success "Database schema updated"
}

# Restart services with zero downtime
restart_services() {
    print_status "Restarting services..."
    
    # Rolling restart to minimize downtime
    local services=("backend" "frontend" "nginx")
    
    for service in "${services[@]}"; do
        print_status "Restarting $service..."
        docker-compose up -d --no-deps "$service"
        
        # Wait for service to be ready
        sleep 10
        
        if docker-compose ps "$service" | grep -q "Up"; then
            print_success "$service restarted successfully"
        else
            print_error "$service failed to restart"
            docker-compose logs "$service"
            exit 1
        fi
    done
    
    print_success "All services restarted"
}

# Post-update health check
post_update_check() {
    print_status "Running post-update health checks..."
    
    sleep 30  # Wait for services to fully initialize
    
    # Check if all services are running
    local services=("postgres" "redis" "backend" "frontend" "nginx")
    local failed_services=()
    
    for service in "${services[@]}"; do
        if ! docker-compose ps "$service" | grep -q "Up"; then
            failed_services+=("$service")
        fi
    done
    
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        print_error "Failed services after update: ${failed_services[*]}"
        return 1
    fi
    
    # Test API endpoint
    if ! curl -sf http://localhost:8000/health > /dev/null; then
        print_error "API health check failed"
        return 1
    fi
    
    # Test frontend
    if ! curl -sf http://localhost:3000 > /dev/null; then
        print_error "Frontend health check failed"
        return 1
    fi
    
    print_success "All post-update health checks passed"
}

# Rollback function
rollback() {
    print_error "Update failed, initiating rollback..."
    
    local latest_backup=$(ls -1t "$BACKUP_DIR" | grep "pre_update_backup_" | head -n 1)
    
    if [[ -z "$latest_backup" ]]; then
        print_error "No backup found for rollback"
        exit 1
    fi
    
    print_status "Rolling back to: $latest_backup"
    
    # Stop services
    docker-compose down
    
    # Restore database
    docker-compose up -d postgres
    sleep 10
    docker-compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS trading_db;"
    docker-compose exec -T postgres psql -U postgres -c "CREATE DATABASE trading_db OWNER trading_user;"
    docker-compose exec -T postgres psql -U trading_user -d trading_db < "$BACKUP_DIR/$latest_backup/database.sql"
    
    # Restore application files (if needed)
    # tar -xzf "$BACKUP_DIR/$latest_backup/app_data.tar.gz" -C /
    
    # Restart all services
    docker-compose up -d
    
    print_success "Rollback completed"
}

# Cleanup old images and containers
cleanup() {
    print_status "Cleaning up old images and containers..."
    
    # Remove dangling images
    docker image prune -f
    
    # Remove unused containers
    docker container prune -f
    
    # Remove unused networks
    docker network prune -f
    
    # Remove unused volumes (be careful!)
    read -p "Do you want to remove unused Docker volumes? This may delete data! (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
    fi
    
    print_success "Cleanup completed"
}

# Main update function
main() {
    echo "=========================================="
    echo "  Trading Dashboard Update"
    echo "=========================================="
    echo
    
    # Confirm update
    read -p "Are you sure you want to update the trading dashboard? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Update cancelled by user"
        exit 1
    fi
    
    # Run update steps
    health_check
    create_backup
    update_code
    update_images
    
    # Try to update database and restart services
    if update_database && restart_services && post_update_check; then
        print_success "Update completed successfully!"
        
        # Optional cleanup
        read -p "Do you want to run cleanup? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cleanup
        fi
        
        echo
        print_status "Update Summary:"
        echo "  - Backup created: pre_update_backup_$TIMESTAMP"
        echo "  - All services updated and running"
        echo "  - Health checks passed"
        echo
        print_status "You can now access the updated application"
        
    else
        # Update failed, offer rollback
        print_error "Update failed!"
        read -p "Do you want to rollback to the previous version? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rollback
        else
            print_warning "Rollback skipped. Please check the logs and fix issues manually."
            print_status "Backup location: $BACKUP_DIR/pre_update_backup_$TIMESTAMP"
        fi
    fi
}

# Handle script interruption
trap 'print_error "Update interrupted"; exit 1' INT TERM

# Check if we're in the right directory
if [[ ! -f "docker-compose.yml" ]]; then
    print_error "docker-compose.yml not found. Please run this script from the project root directory."
    exit 1
fi

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi