FROM homeassistant/home-assistant:latest

WORKDIR /config

RUN apk update
RUN apk upgrade
RUN apk add ffmpeg

COPY ./amur .

RUN mkdir /config/custom_components
RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/AlexxIT/XiaomiGateway3.git /tmp/git/XiaomiGateway3
RUN cp -r /tmp/git/XiaomiGateway3/custom_components/* /config/custom_components
RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/mash2k3/qingping_cgs1.git /tmp/git/qingping_cgs1
RUN cp -r /tmp/git/qingping_cgs1/custom_components/* /config/custom_components
RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/icarome/zk_teco.git /tmp/git/zk_teco
RUN cp -r /tmp/git/zk_teco/* /config/custom_components/zk_teco
