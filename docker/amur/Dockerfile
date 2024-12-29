FROM homeassistant/home-assistant:latest

WORKDIR /config

RUN apk -y update
RUN apk -y upgrade
RUN apk install -y ffmpeg

COPY ./amur .

RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/AlexxIT/XiaomiGateway3.git /tmp/git/XiaomiGateway3
RUN mkdir /config/custom_components
RUN cp -r /tmp/git/XiaomiGateway3/custom_components/* /config/custom_components
