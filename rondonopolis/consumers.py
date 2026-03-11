import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Agendamento


class BaseTelaConsumer(AsyncWebsocketConsumer):
    """Consumer base para todas as telas"""
    group_name = None
    
    async def connect(self):
        if not self.group_name:
            await self.close()
            return
            
        # Aceitar a conexão
        await self.accept()
        
        # Adicionar o cliente ao grupo
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

    async def disconnect(self, close_code):
        if self.group_name:
            # Remover o cliente do grupo quando desconectar
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        # Não precisamos receber mensagens do cliente por enquanto
        pass

    async def send_update(self, event):
        # Enviar atualização para o cliente WebSocket
        await self.send(text_data=json.dumps({
            'type': event['type'],
            'action': event['action'],
            'agendamento_id': event.get('agendamento_id'),
            'message': event.get('message', ''),
            'data': event.get('data', {}),
        }))


class PortariaConsumer(BaseTelaConsumer):
    group_name = 'portaria_updates'
    
    async def portaria_update(self, event):
        await self.send_update(event)


class ChecklistConsumer(BaseTelaConsumer):
    group_name = 'checklist_updates'
    
    async def checklist_update(self, event):
        await self.send_update(event)


class ArmazemConsumer(BaseTelaConsumer):
    group_name = 'armazem_updates'
    
    async def armazem_update(self, event):
        await self.send_update(event)


class OndaConsumer(BaseTelaConsumer):
    group_name = 'onda_updates'
    
    async def onda_update(self, event):
        await self.send_update(event)


class DocumentosConsumer(BaseTelaConsumer):
    group_name = 'documentos_updates'
    
    async def documentos_update(self, event):
        await self.send_update(event)

