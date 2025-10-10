# https://github.com/docker-library/haproxy/blob/master/2.8/alpine/Dockerfile
FROM haproxy:lts-alpine3.22

# Copy HAProxy configuration
COPY haproxy.cfg /usr/local/etc/haproxy/haproxy.cfg

# Expose HTTP and HTTPS ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# Start HAProxy
CMD ["haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg"]
