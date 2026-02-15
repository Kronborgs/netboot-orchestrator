FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    dnsmasq \
    curl \
    git \
    build-essential \
    gcc \
    make \
    perl \
    mkisofs \
    syslinux \
    && rm -rf /var/lib/apt/lists/*

COPY config/ /tftp/config/
COPY scripts/ /tftp/scripts/
COPY entrypoint.sh /entrypoint.sh
COPY build-custom-undionly.sh /entrypoint-build.sh

RUN chmod +x /entrypoint.sh /entrypoint-build.sh

EXPOSE 69/udp 67/udp

VOLUME ["/data"]

ENTRYPOINT ["/entrypoint.sh"]
