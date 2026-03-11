from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/portaria/$', consumers.PortariaConsumer.as_asgi()),
    re_path(r'^ws/checklist/$', consumers.ChecklistConsumer.as_asgi()),
    re_path(r'^ws/armazem/$', consumers.ArmazemConsumer.as_asgi()),
    re_path(r'^ws/onda/$', consumers.OndaConsumer.as_asgi()),
    re_path(r'^ws/documentos/$', consumers.DocumentosConsumer.as_asgi()),
]

