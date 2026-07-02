from celery import Celery

app = Celery('mq',
             broker='amqp://localhost',
             include=['mq.tasks'])

if __name__ == '__main__':
    app.start()