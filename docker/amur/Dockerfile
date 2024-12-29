FROM homeassistant/home-assistant:latest

WORKDIR /config

COPY ./amur .

RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/AlexxIT/XiaomiGateway3.git /tmp/git/XiaomiGateway3
RUN mkdir /config/custom_components
RUN cp -r /tmp/git/XiaomiGateway3/custom_components/* /config/custom_components
RUN git clone https://ruslanruslanruslan:$GITHUB_KEY@github.com/nergal/homeassistant-vacuum-viomi.git /tmp/git/homeassistant-vacuum-viomi
RUN cp -r /tmp/git/homeassistant-vacuum-viomi/custom_components/* /config/custom_components