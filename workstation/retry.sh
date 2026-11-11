#!/bin/bash
# Usage: retry <attempts> <command...>
# Re-runs a command with linear backoff. For build steps that depend on
# flaky upstream services (e.g. Launchpad's PPA signing-key API, which
# intermittently 500s with GPGKeyTemporarilyNotFoundError) - a transient
# upstream error shouldn't cost a full CI rerun.
attempts=$1
shift
for ((i = 1; i <= attempts; i++)); do
    "$@" && exit 0
    [ "$i" -lt "$attempts" ] || break
    echo "retry: attempt $i/$attempts failed: $*; retrying in $((i * 20))s" >&2
    sleep $((i * 20))
done
echo "retry: giving up after $attempts attempts: $*" >&2
exit 1
