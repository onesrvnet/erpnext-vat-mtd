# Setup this repo for developing

1. Start the devcontainers in .devcontainers using docker compose.
2. Create a new bench using `bench init --skip-redis-config-generation frappe-bench`
We'll need to setup redis later if needed.
3. Setup frappe with devcontainer service
```
# DB host is the MariaDB service from the compose
bench set-config -g db_host mariadb

# Redis services (names may already match your .devcontainer/docker-compose.yml)
bench set-config -g redis_cache    redis://redis-cache:6379
bench set-config -g redis_queue    redis://redis-queue:6379
bench set-config -g redis_socketio redis://redis-queue:6379
```

4. Setup bench site `bench new-site localhost`
5. Mysql root PW: `123
6. Install erpnext: `bench get-app erpnext --branch=version-15` `bench install-app erpnext`
7. Setup erpnext
8. Install uk_vat locally: `bench get-app --resolve-deps /workspace --soft-link` `bench install-app uk_vat`