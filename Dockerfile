#Build stage
FROM python:3.8.12-alpine3.15 AS builder 

LABEL maintainer="Wasin Waeosri <wasin.waeosri@lseg.com>"

# Install gcc + musl-dev
RUN apk update && apk add --no-cache build-base gcc musl-dev 
#Copy requirements.txt
COPY requirements.txt .

# install dependencies to the local user directory (eg. /root/.local)
RUN pip install --user -r requirements.txt

# Run stage
FROM python:3.8.12-alpine3.15
WORKDIR /app

# Update PATH environment variable + set Python buffer to make Docker print every message instantly.
ENV PATH=/root/.local:$PATH \
    PYTHONUNBUFFERED=1

# copy only the dependencies installation from the 1st stage image
COPY --from=builder /root/.local /root/.local
COPY mrn_console_app.py .

#Run Python
ENTRYPOINT ["python", "./mrn_console_app.py"]