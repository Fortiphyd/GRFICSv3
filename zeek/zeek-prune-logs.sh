#!/bin/sh
# Zeek log-rotation postprocessor (local.zeek: Log::default_rotation_
# postprocessor_cmd). Zeek passes: <rotated file> <base name> <open ts>
# <close ts> <terminating> <writer>, after it has already renamed the file
# to <base>.<YYYY-MM-DD-HH-MM-SS>.log.
LOG_DIR=/usr/local/zeek/logs

# 1. Recreate the live file empty. Zeek only creates <base>.log on its next
#    write, and the Wazuh agent loses the lines that create a file it's
#    watching (it picks the new file up, but past them) - seen live: the
#    first PLC program upload after Zeek (re)started never reached Wazuh,
#    every later one did. Zeek writes into an existing file in place (same
#    inode), so a pre-made empty file is followed from its first line.
[ -n "$2" ] && touch "$LOG_DIR/$2.log"

# 2. Prune. Standalone Zeek (no zeekctl) never deletes anything, and with
#    full Modbus parsing the logs grew ~300 MB/hour - several GB over a
#    class day on a student laptop. Drop rotated files closed more than
#    RETAIN_MINUTES ago; the live <base>.log never matches the dated pattern.
RETAIN_MINUTES=${ZEEK_LOG_RETAIN_MINUTES:-120}
find "$LOG_DIR" -maxdepth 1 -type f \
    -name '*.[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-*.log' \
    -mmin +"$RETAIN_MINUTES" -delete
exit 0
