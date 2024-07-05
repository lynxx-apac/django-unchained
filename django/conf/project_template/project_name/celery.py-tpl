import os
from pathlib import Path

from celery import Celery

MAIN_APP_DIR = Path(__file__).resolve().parent

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'{MAIN_APP_DIR.name}.settings')
app = Celery(MAIN_APP_DIR.name)  # , broker='amqp://', backend='amqp://')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
