from celery import Celery

app = Celery('Face_Crawler',
             backend='rpc://',
             broker='amqp://rabbitmq',
             include='tasks')
