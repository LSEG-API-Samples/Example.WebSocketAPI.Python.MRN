#Build stage
ARG PYTHON_VERSION=3.10
ARG VARIANT=slim-bookworm
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder 

LABEL maintainer="LSEG Developer Relations"

#Copy requirements.txt
COPY requirements.txt .

# ------------ Begin: For run in internal LSEG ZScaler environment ------------
#Image runs internet requests over HTTPS – Install Certs if dev environment

#Add the CA Certificate to the container
ADD ./ZscalerRootCerttificate.pem /usr/local/share/ca-certificates/ZscalerRootCertificate-2048-SHA256.crt
RUN chmod 644 /usr/local/share/ca-certificates/ZscalerRootCertificate-2048-SHA256.crt && update-ca-certificates
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# ------------ End: For run in internal LSEG ZScaler environment ------------

#Continue the build where the HTTPS Connections are made

# install dependencies to the local user directory (eg. /root/.local)
RUN pip install --no-cache-dir --user -r requirements.txt

# Run stage
FROM --platform=linux/amd64 python:${PYTHON_VERSION}-alpine3.20
WORKDIR /app

# Update PATH environment variable + set Python buffer to make Docker print every message instantly.
ENV PATH=/root/.local:$PATH \
    PYTHONUNBUFFERED=1

# copy only the dependencies installation from the 1st stage image
COPY --from=builder /root/.local /root/.local
COPY mrn_console_rto_v2.py .

#Run Python
ENTRYPOINT ["python", "mrn_console_rto_v2.py"]