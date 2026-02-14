FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    dnsmasq \
    && rm -rf /var/lib/apt/lists/*

COPY config/ /tftp/config/
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 69/udp 67/udp

VOLUME ["/data"]

ENTRYPOINT ["/entrypoint.sh"]
