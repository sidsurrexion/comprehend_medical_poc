FROM python:3.6
ENV APP_DIR=/opt/fenix
RUN mkdir $APP_DIR
COPY . $APP_DIR/
WORKDIR $APP_DIR
RUN pip install --upgrade --no-cache-dir -r requirements.txt