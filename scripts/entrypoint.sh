#!/bin/sh
if [ -n "$PUID" ] && [ -n "$PGID" ]; then
    groupadd -g $PGID mygroup
    useradd -u $PUID -g mygroup -s /bin/sh -m myuser
    chown -R myuser:mygroup /app
    exec su-exec myuser "$@"
else
    exec "$@"
fi