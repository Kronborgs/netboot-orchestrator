FROM nginx:alpine

COPY conf/nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 80

VOLUME ["/data"]

ENTRYPOINT ["/entrypoint.sh"]
