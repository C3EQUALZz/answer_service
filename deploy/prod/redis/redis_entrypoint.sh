#!/bin/sh
# Redis reads no environment variables in its config file, so both are generated.
set -eu

: "${REDIS_DEFAULT_PASSWORD:?REDIS_DEFAULT_PASSWORD must be set}"
: "${REDIS_USER:?REDIS_USER must be set}"
: "${REDIS_PASSWORD:?REDIS_PASSWORD must be set}"

CONFIG_DIR=/usr/local/etc/redis
mkdir -p "${CONFIG_DIR}"

cat > "${CONFIG_DIR}/redis.conf" <<CONF
bind 0.0.0.0
protected-mode yes

appendonly yes
appendfsync everysec

# Eviction off: a dropped schedule fails silently, a refused write does not.
maxmemory-policy noeviction
CONF

# `default` is the operator (healthcheck, redis-cli); the app gets its own user.
# CLIENT|SETINFO is granted back because redis-py sends it on every connect.
cat > "${CONFIG_DIR}/users.acl" <<ACL
user default on >${REDIS_DEFAULT_PASSWORD} ~* &* +@all
user ${REDIS_USER} on >${REDIS_PASSWORD} ~* &* +@all -@admin -@dangerous +client|setinfo
ACL

chmod 600 "${CONFIG_DIR}/users.acl"

exec redis-server "${CONFIG_DIR}/redis.conf" --aclfile "${CONFIG_DIR}/users.acl"
