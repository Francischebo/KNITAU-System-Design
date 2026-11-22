from __future__ import annotations

import os
from celery import Celery
from kombu import Exchange, Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("knitau")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Isolated queues protect financial M-Pesa payouts from bulk SMS/export traffic spikes
app.conf.task_queues = (
    Queue("payments_mpesa", Exchange("payments_mpesa"), routing_key="payments.#"),
    Queue("notifications", Exchange("notifications"), routing_key="notifications.#"),
    Queue("matching", Exchange("matching"), routing_key="matching.#"),
    Queue("exports", Exchange("exports"), routing_key="exports.#"),
    Queue("default", Exchange("default"), routing_key="default.#"),
)
app.conf.task_default_queue = "default"
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
app.conf.worker_prefetch_multiplier = 1

app.autodiscover_tasks()
