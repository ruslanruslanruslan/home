FROM homeassistant/home-assistant:latest

WORKDIR /config

# RUN apk update --no-cache --ignore alpine-baselayout
# RUN apk upgrade
RUN apk add ffmpeg

RUN mkdir -p /tmp/config/custom_components
RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/al-one/hass-xiaomi-miot.git /tmp/git/hass-xiaomi-miot
RUN cp -r /tmp/git/hass-xiaomi-miot/custom_components/* /tmp/config/custom_components
RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/make-all/tuya-local.git /tmp/git/tuya-local
RUN cp -r /tmp/git/tuya-local/custom_components/* /tmp/config/custom_components
RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/rospogrigio/localtuya.git /tmp/git/localtuya
RUN cp -r /tmp/git/localtuya/custom_components/* /tmp/config/custom_components
RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/blakeblackshear/frigate-hass-integration.git /tmp/git/frigate-hass-integration
RUN cp -r /tmp/git/frigate-hass-integration/custom_components/* /tmp/config/custom_components
RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/tomaae/homeassistant-mikrotik_router.git /tmp/git/homeassistant-mikrotik_router
RUN cp -r /tmp/git/homeassistant-mikrotik_router/custom_components/* /tmp/config/custom_components

# will be copied later on deploy
# COPY ./iot/homeassistant/mati/config/* /tmp/config/
