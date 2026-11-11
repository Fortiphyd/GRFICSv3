# A throwaway "visiting device" image for the noise floor's benign ARP
# churn event (docs/cyber-vs-physical-fault-injection-design.md §5).
# simulation/noise_floor/arp_churn.py creates and destroys short-lived
# containers from this image to simulate a legitimate device
# reconnecting/renewing its lease - a fresh container on the same IP
# gets a fresh MAC from Docker every time, which is exactly the
# "changed_mac" signature a real device swap would produce too.
#
# Built locally (not pulled from a registry at session runtime) so this
# works in an air-gapped training deployment the same as every other
# fortiphyd/grfics-* image. Alpine's busybox ping is all this needs -
# just enough to force a real ARP exchange with the router.
FROM alpine:3.20
ARG BUILD_VERSION=unknown
ARG BUILD_CREATED=unknown
LABEL org.opencontainers.image.version=${BUILD_VERSION}
LABEL org.opencontainers.image.created=${BUILD_CREATED}
CMD ["sleep", "infinity"]
