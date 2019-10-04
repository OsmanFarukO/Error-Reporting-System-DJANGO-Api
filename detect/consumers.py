from django.conf import settings

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from oauth2_provider.models import AccessToken
from .utils import get_user_from_oauth


class AdminComsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        
    async def receive_json(self, content):
        command = content.get("command", None)
        if command == 'add_corporation_group':
            await self.corporation_group_add(content['oauth_token'])

    async def corporation_group_add(self, tkn):
        user = await get_user_from_oauth(tkn)
        print('<<>> ', user)
        self.scope['userid'] = user['user_id']

        await self.channel_layer.group_add(
            str(user['corp_id']),
            self.channel_name,
        )
