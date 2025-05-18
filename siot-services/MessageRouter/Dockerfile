FROM python:3.12.1-alpine 

COPY ./code /etc/usr/src/app

WORKDIR /etc/usr/src/app

RUN pip3 install -r requirements.txt

CMD ["python", "MessageRouter.py"]