FROM haproxy:lts-alpine3.22

RUN apk add --no-cache \
    curl \
    bind-tools \
    iputils \
    tcpdump \
    netcat-openbsd \
    wget \
    net-tools \
    busybox-extras

# Copy HAProxy configuration
COPY haproxy.cfg /usr/local/etc/haproxy/haproxy.cfg

# Expose HTTP and HTTPS ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# Start HAProxy
CMD ["haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg"]
