FROM python:3.7-alpine

LABEL maintainer="Wasin Waeosri <wasin.waeosri@rifinitiv.com>"
LABEL build_date="2021-05-18"
# set working directory
WORKDIR /app

# Copy requirements.txt first 
COPY requirements.txt .
# instruction to be run during image build
RUN pip install -r requirements.txt

# then copy the application
COPY mrn_console_app.py .

ENTRYPOINT ["python", "./mrn_console_app.py"]