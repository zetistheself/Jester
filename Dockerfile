FROM teddysun/xray

RUN apk add iproute2

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ARG TRANSFER_RATE
ENV TRANSFER_RATE=${TRANSFER_RATE}

ENTRYPOINT ["/entrypoint.sh"]

COPY xray-config.json /etc/xray/config.json

CMD ["xray", "-config", "/etc/xray/config.json"]
