#Build stage
FROM python:3.8-alpine3.14 AS builder

LABEL maintainer="Wasin Waeosri <wasin.waeosri@rifinitiv.com>"

# Install gcc + musl-dev
RUN apk add --no-cache gcc musl-dev
#Copy requirements.txt
COPY requirements.txt .

# install dependencies to the local user directory (eg. /root/.local)
RUN pip install --user -r requirements.txt

# Run stage
#FROM python:3.8.11-alpine
FROM python:3.8.11-alpine3.14
WORKDIR /app

# Update PATH environment variable + set Python buffer to make Docker print every message instantly.
ENV PATH=/root/.local:$PATH \
    PYTHONUNBUFFERED=1

# copy only the dependencies installation from the 1st stage image
COPY --from=builder /root/.local /root/.local
COPY mrn_console_app.py .

#Run Python
ENTRYPOINT ["python", "./mrn_console_app.py"]