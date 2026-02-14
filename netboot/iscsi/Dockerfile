FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    tgt \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /entrypoint.sh
COPY init_iscsi.sh /init_iscsi.sh

RUN chmod +x /entrypoint.sh /init_iscsi.sh

EXPOSE 3260

VOLUME ["/data"]

ENTRYPOINT ["/entrypoint.sh"]
