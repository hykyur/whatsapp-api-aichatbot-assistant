from celery import Celery

app = Celery('celery',
             broker='amqp://localhost',
             include=['celery.tasks'])

if __name__ == '__main__':
    app.start()