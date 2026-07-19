#!/bin/sh
# Redis reads no environment variables in its config file, so the config and the
# ACL are generated here from the environment instead of being baked in.
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

# Scheduled tasks and task results must survive a restart, so eviction is off:
# under memory pressure Redis should refuse writes loudly rather than silently
# drop a schedule nobody notices is gone.
maxmemory-policy noeviction
CONF

# Two users, because they are not the same principal:
#
#   default  - operator. Full access, used by the healthcheck and by a human
#              with redis-cli.
#   \$REDIS_USER - the application. Everything it needs to store results and
#              schedules, minus the command groups it has no business calling.
#
# -@dangerous drops FLUSHALL, FLUSHDB, KEYS, CONFIG, SHUTDOWN and DEBUG;
# -@admin drops replication and cluster control. CLIENT|SETINFO is granted back
# explicitly because redis-py sends it on every connect to identify itself.
cat > "${CONFIG_DIR}/users.acl" <<ACL
user default on >${REDIS_DEFAULT_PASSWORD} ~* &* +@all
user ${REDIS_USER} on >${REDIS_PASSWORD} ~* &* +@all -@admin -@dangerous +client|setinfo
ACL

chmod 600 "${CONFIG_DIR}/users.acl"

exec redis-server "${CONFIG_DIR}/redis.conf" --aclfile "${CONFIG_DIR}/users.acl"
