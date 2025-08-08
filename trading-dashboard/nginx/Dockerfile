FROM nginx:alpine

# Install certbot for SSL certificates
RUN apk add --no-cache certbot certbot-nginx openssl curl

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create SSL directory
RUN mkdir -p /etc/nginx/ssl

# Create self-signed certificate for development/initial setup
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/trading-dashboard.key \
    -out /etc/nginx/ssl/trading-dashboard.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose ports
EXPOSE 80 443

# Use custom entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]