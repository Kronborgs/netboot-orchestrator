# Download and verify iPXE binaries, add boot scripts
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    dnsmasq \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create TFTP directories
RUN mkdir -p /tftp

COPY config/ /tftp/config/
COPY scripts/ /tftp/scripts/
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

# Download standard iPXE binaries at build time
WORKDIR /tftp
RUN echo "Downloading iPXE bootloaders..." && \
    curl -L -o undionly.kpxe https://boot.ipxe.org/undionly.kpxe && \
    curl -L -o ipxe.efi https://boot.ipxe.org/ipxe.efi && \
    ls -lh undionly.kpxe ipxe.efi && \
    echo "✓ iPXE binaries ready"

EXPOSE 69/udp 67/udp

VOLUME ["/data"]

ENTRYPOINT ["/entrypoint.sh"]
