FROM homeassistant/home-assistant:latest

WORKDIR /config

# RUN apk update --no-cache --ignore alpine-baselayout
# RUN apk upgrade
RUN apk add ffmpeg

RUN mkdir /config/custom_components
RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/AlexxIT/XiaomiGateway3.git /tmp/git/XiaomiGateway3
RUN cp -r /tmp/git/XiaomiGateway3/custom_components/* /config/custom_components
RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/al-one/hass-xiaomi-miot.git /tmp/git/hass-xiaomi-miot
RUN cp -r /tmp/git/hass-xiaomi-miot/custom_components/* /config/custom_components
RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/blakeblackshear/frigate-hass-integration.git /tmp/git/advanced-camera-card
RUN cp -r /tmp/git/advanced-camera-card/custom_components/* /config/custom_components
