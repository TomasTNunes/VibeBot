#!/bin/sh
# Run the application as the specified user (PUID/PGID) if provided
if [ -n "$PUID" ] && [ -n "$PGID" ]; then
    groupadd -g "$PGID" vibebot
    useradd -m -u "$PUID" -g "$PGID" vibebot
    exec gosu vibebot "$@"
else
    exec "$@"
fi