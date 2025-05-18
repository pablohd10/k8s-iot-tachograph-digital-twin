FROM python:3.12

COPY ./code /etc/usr/src/app

WORKDIR /etc/usr/src/app

RUN pip install -r requirements.txt

CMD ["python", "events_manager_api.py"]