FROM debian:bookworm-slim AS builder
# Optional interpreter mode for build validation under CPU emulation.
ARG MONO_ENV_OPTIONS
ARG DUMP1090_COMMIT=0339a57b89cd6e61856cbb13ae342c31ae7be5ac
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl pkg-config librtlsdr-dev libusb-1.0-0-dev \
    libncurses-dev mono-mcs && rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN curl -fsSL --retry 3 "https://codeload.github.com/flightaware/dump1090/tar.gz/${DUMP1090_COMMIT}" \
      | tar -xz --strip-components=1 && \
    make -j2 RTLSDR=yes BLADERF=no HACKRF=no LIMESDR=no SOAPYSDR=no \
      DUMP1090_VERSION="${DUMP1090_COMMIT}" dump1090
WORKDIR /opt/vrs
# Upstream URLs are mutable; checksums ensure an upstream change cannot silently enter a build.
RUN curl -fsSL --retry 3 https://www.virtualradarserver.co.uk/Files/VirtualRadar.tar.gz -o /tmp/vrs.tar.gz && \
    echo 'b3d956b4e049c97b4fec93452ac5ad14225b3e9b732ed62aeceb1e6cf5b24344  /tmp/vrs.tar.gz' | sha256sum -c - && \
    tar -xzf /tmp/vrs.tar.gz && \
    curl -fsSL --retry 3 https://www.virtualradarserver.co.uk/Files/VirtualRadar.WebAdminPlugin.tar.gz -o /tmp/admin.tar.gz && \
    echo 'affa6a92d0454109f5d39d32888a208dee547fb30871719f5ba5ceca2bedf215  /tmp/admin.tar.gz' | sha256sum -c - && \
    tar -xzf /tmp/admin.tar.gz
RUN apt-get update && apt-get install -y --no-install-recommends libmono-windowsbase4.0-cil
COPY Configure.cs /build/Configure.cs
RUN mcs -r:WindowsBase -r:VirtualRadar.Library.dll -r:VirtualRadar.Interface.dll -r:InterfaceFactory.dll \
    -out:/opt/vrs/Configure.exe /build/Configure.cs

FROM debian:bookworm-slim AS artwork
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl unzip \
    && rm -rf /var/lib/apt/lists/*
ARG ARTWORK_COMMIT=c4b208370081e849af3106b6e1d78b5140b28a97
WORKDIR /opt/vrs-artwork
RUN curl -fsSL --retry 3 "https://raw.githubusercontent.com/rikgale/VRSOperatorFlags/${ARTWORK_COMMIT}/OperatorFlags.zip" -o /tmp/flags.zip && \
    echo '94283cb1c17386aac75312f786a146e1e5dc0ec186a6a90b659b0d1a99e5ecc4  /tmp/flags.zip' | sha256sum -c - && \
    curl -fsSL --retry 3 "https://raw.githubusercontent.com/rikgale/VRSOperatorFlags/${ARTWORK_COMMIT}/Silhouettes.zip" -o /tmp/silhouettes.zip && \
    echo '67e1b6e29249a4236f4f8324e289018f372c7f337fdb3e55de02bc7a1a8239b5  /tmp/silhouettes.zip' | sha256sum -c - && \
    unzip -q /tmp/flags.zip -d OperatorFlags && \
    unzip -q /tmp/silhouettes.zip -d Silhouettes && \
    rm /tmp/flags.zip /tmp/silhouettes.zip && \
    find . -type d -exec chmod 755 {} + && find . -type f -exec chmod 644 {} +
COPY ARTWORK-LICENSE.txt LICENSE.txt
COPY ARTWORK-NOTICE.md NOTICE.md

FROM debian:bookworm-slim
ARG MONO_ENV_OPTIONS
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates mono-runtime libmono-windowsbase4.0-cil libmono-system-windows-forms4.0-cil \
    libmono-system-web4.0-cil libmono-system-serviceprocess4.0-cil \
    libmono-system-runtime-serialization4.0-cil libmono-sqlite4.0-cil \
    libgdiplus fonts-dejavu-core librtlsdr0 libusb-1.0-0 libncurses6 \
    nginx python3 && rm -rf /var/lib/apt/lists/* /etc/nginx/sites-enabled/default
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmono-system-xml-linq4.0-cil libmono-system-net-http4.0-cil \
    libmono-system-servicemodel4.0a-cil libmono-system-servicemodel-web4.0-cil \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/dump1090 /usr/local/bin/dump1090
COPY --from=builder /build/LICENSE /usr/share/doc/dump1090/LICENSE
COPY --from=builder /opt/vrs /opt/vrs
COPY --from=artwork /opt/vrs-artwork /opt/vrs-artwork
COPY VRS-LICENSE.txt /opt/vrs/LICENSE.txt
COPY VirtualRadar.exe.config /opt/vrs/VirtualRadar.exe.config
COPY nginx.conf /etc/nginx/nginx.conf
COPY run.py index.html /app/
WORKDIR /opt/vrs
ENV HOME=/data XDG_DATA_HOME=/data/.local/share
CMD ["python3", "-u", "/app/run.py"]

ARG BUILD_VERSION=0.1.3
ARG BUILD_ARCH=amd64
LABEL io.hass.version="${BUILD_VERSION}" io.hass.type="app" io.hass.arch="${BUILD_ARCH}" \
    org.opencontainers.image.source="https://github.com/maxneuvians/home-assistant-apps"
