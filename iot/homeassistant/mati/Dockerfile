FROM homeassistant/home-assistant:latest

WORKDIR /config

# RUN apk update --no-cache --ignore alpine-baselayout
# RUN apk upgrade
RUN apk add ffmpeg

RUN mkdir -p /tmp/config/custom_components
RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/blakeblackshear/frigate-hass-integration.git /tmp/git/frigate-hass-integration
RUN cp -r /tmp/git/frigate-hass-integration/custom_components/* /tmp/config/custom_components

# will be copied later on deploy
# COPY ./iot/homeassistant/mati/config/* /tmp/config/