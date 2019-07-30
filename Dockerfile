FROM python:3.7-alpine

LABEL maintainer="Wasin Waeosri <wasin.waeosri@rifinitiv.com>"
LABEL build_date="2019-07-30"

# Copy requirements.txt first 
COPY requirements.txt /
# instruction to be run during image build
RUN pip install -r requirements.txt

# then copy the application
RUN mkdir /app
COPY mrn_console_app.py /app
WORKDIR /app

ENTRYPOINT ["python", "/app/mrn_console_app.py"]