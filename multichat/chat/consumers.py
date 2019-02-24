from django.conf import settings

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core import serializers
from .exceptions import ClientError
from .utils import get_room_or_error, get_players_or_error, add_player_to_room, ready_player


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    This chat consumer handles websocket connections for chat clients.

    It uses AsyncJsonWebsocketConsumer, which means all the handling functions
    must be async functions, and any sync work (like ORM access) has to be
    behind database_sync_to_async or sync_to_async. For more, read
    http://channels.readthedocs.io/en/latest/topics/consumers.html
    """

    ##### WebSocket event handlers
    async def connect(self):
        """
        Called when the websocket is handshaking as part of initial connection.
        """
        # Are they logged in?
        if self.scope["user"].is_anonymous:
            # Reject the connection
            await self.close()
        else:
            # Accept the connection
            await self.accept()
        # Store which rooms the user has joined on this connection
        self.rooms = set()

        # Store which users are in a current room

    async def receive_json(self, content):
        """
        Called when we get a text frame. Channels will JSON-decode the payload
        for us and pass it as the first argument.
        """
        # Messages will have a "command" key we can switch on
        command = content.get("command", None)
        try:
            if command == "join":
                # Make them join the room
                await self.join_room(content["room"])
            elif command == "ready":
                await self.ready_up(content["room"])
            elif command == "leave":
                # Leave the room
                await self.leave_room(content["room"])
            elif command == "send":
                print(content)
                await self.send_room(content["room"], content["message"])
            elif command == "draw":
                print("drawing")
                print(content["image"])
                print(content["room"])
                await self.send_room_draw(content["room"], content["image"], content["target_player"])
        except ClientError as e:
            # Catch any errors and send it back
            await self.send_json({"error": e.code})

    async def disconnect(self, code):
        """
        Called when the WebSocket closes for any reason.
        """
        print('disconnecting')
        # Leave all the rooms we are still in
        for room_id in list(self.rooms):
            try:
                await self.leave_room(room_id)
            except ClientError:
                pass

    ##### Command helper methods called by receive_json

    async def join_room(self, room_id):
        """
        Called by receive_json when someone sent a join command.
        """
        # The logged-in user is in our scope thanks to the authentication ASGI middleware
        added = await add_player_to_room(room_id, self.scope["user"])
        room = await get_room_or_error(room_id, self.scope["user"])
        players = await get_players_or_error(room_id, self.scope["user"])
        # Send a join message if it's turned on
        if settings.NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS:
            await self.channel_layer.group_send(
                room.group_name,
                {
                    "type": "chat.join",
                    "room_id": room_id,
                    "username": self.scope["user"].username,
                    "players": list(players.values('username', 'id', 'ready'))
                }
            )
        # Store that we're in the room
        self.rooms.add(room_id)
        # Add them to the group so they get room messages
        await self.channel_layer.group_add(
            room.group_name,
            self.channel_name,
        )
        # Instruct their client to finish opening the room
        await self.send_json({
            "join": str(room.id),
            "title": room.title,
            "username": self.scope["user"].username,
            "players": list(players.values('username', 'id', 'ready'))
        })

    async def leave_room(self, room_id):
        """
        Called by receive_json when someone sent a leave command.
        """
        # The logged-in user is in our scope thanks to the authentication ASGI middleware
        room = await get_room_or_error(room_id, self.scope["user"])
        removed = await remove_player_from_room(room_id, self.scope["user"])
        # Send a leave message if it's turned on
        if settings.NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS:
            await self.channel_layer.group_send(
                room.group_name,
                {
                    "type": "chat.leave",
                    "room_id": room_id,
                    "username": self.scope["user"].username,
                }
            )
        # Remove that we're in the room
        self.rooms.discard(room_id)
        self.users.remove(self.scope["user"].username)
        # Remove them from the group so they no longer get room messages
        await self.channel_layer.group_discard(
            room.group_name,
            self.channel_name,
        )
        # Instruct their client to finish closing the room
        await self.send_json({
            "leave": str(room.id),
        })

    async def send_room(self, room_id, message):
        """
        Called by receive_json when someone sends a message to a room.
        """
        # Check they are in this room
        if room_id not in self.rooms:
            raise ClientError("ROOM_ACCESS_DENIED")
        # Get the room and send to the group about it
        room = await get_room_or_error(room_id, self.scope["user"])
        await self.channel_layer.group_send(
            room.group_name,
            {
                "type": "chat.message",
                "room_id": room_id,
                "username": self.scope["user"].username,
                "message": message,
            }
        )

    async def send_room_draw(self, room_id, image, target_player):
        """
        Called by receive_json when someone sends a message to a room.
        """
        print("HERE")
        print(self.rooms)
        print(room_id)
        # Check they are in this room
        if room_id not in self.rooms:
            raise ClientError("ROOM_ACCESS_DENIED")
        # Get the room and send to the group about it
        room = await get_room_or_error(room_id, self.scope["user"])
        await self.channel_layer.group_send(
            room.group_name,
            {
                "type": "chat.image",
                "room_id": room_id,
                "username": self.scope["user"].username,
                "image": image,
            }
        )

    async def ready_up(self, room_id):
        """
        Called by receive_json when someone readys up
        """
        # Check they are in this room
        if room_id not in self.rooms:
            raise ClientError("ROOM_ACCESS_DENIED")
        # Get the room and send to the group about it
        readied = await ready_player(self.scope["user"])
        room = await get_room_or_error(room_id, self.scope["user"])
        players = await get_players_or_error(room_id, self.scope["user"])
        await self.channel_layer.group_send(
            room.group_name,
            {
                "type": "chat.ready",
                "room_id": room_id,
                "username": self.scope["user"].username,
                "players": list(players.values('username', 'id', 'ready'))
            }
        )

    ##### Handlers for messages sent over the channel layer

    # These helper methods are named by the types we send - so chat.join becomes chat_join
    async def chat_join(self, event):
        """
        Called when someone has joined our chat.
        """
        players = await get_players_or_error(event["room_id"], self.scope["user"])
        # Send a message down to the client
        await self.send_json(
            {
                "msg_type": settings.MSG_TYPE_ENTER,
                "room": event["room_id"],
                "username": event["username"],
                "players": list(players.values('username', 'id', 'ready'))
            },
        )

    async def chat_ready(self, event):
        """
        Called when someone has readied up.
        """
        players = await get_players_or_error(event["room_id"], self.scope["user"])
        # Send a message down to the client
        await self.send_json(
            {
                "msg_type": settings.MSG_TYPE_READY,
                "room": event["room_id"],
                "username": event["username"],
                "players": list(players.values('username', 'id', 'ready'))
            },
        )

    async def chat_leave(self, event):
        """
        Called when someone has left our chat.
        """
        # Send a message down to the client
        await self.send_json(
            {
                "msg_type": settings.MSG_TYPE_LEAVE,
                "room": event["room_id"],
                "username": event["username"],
            },
        )

    async def chat_message(self, event):
        """
        Called when someone has messaged our chat.
        """
        # Send a message down to the client
        await self.send_json(
            {
                "msg_type": settings.MSG_TYPE_MESSAGE,
                "room": event["room_id"],
                "username": event["username"],
                "message": event["message"],
            },
        )

    async def chat_image(self, event):
        """
        Called when someone updates an image in the chat.
        """
        # Send a message down to the client
        await self.send_json(
            {
                "msg_type": settings.MSG_TYPE_IMAGE,
                "room": event["room_id"],
                "username": event["username"],
                "image": event["image"],
            },
        )