from channels.db import database_sync_to_async

from .exceptions import ClientError
from .models import Room, User


# This decorator turns this function from a synchronous function into an async one
# we can call from our async consumers, that handles Django DBs correctly.
# For more, see http://channels.readthedocs.io/en/latest/topics/databases.html
@database_sync_to_async
def get_room_or_error(room_id, user):
    """
    Tries to fetch a room for the user, checking permissions along the way.
    """
    # Check if the user is logged in
    if not user.is_authenticated:
        raise ClientError("USER_HAS_TO_LOGIN")
    # Find the room they requested (by ID)
    try:
        room = Room.objects.get(pk=room_id)
    except Room.DoesNotExist:
        raise ClientError("ROOM_INVALID")
    # Check permissions
    if room.staff_only and not user.is_staff:
        raise ClientError("ROOM_ACCESS_DENIED")
    return room

@database_sync_to_async
def get_players_or_error(room_id, user):
    """
    Tries to fetch all the players in a room, checking permissions along the way.
    """
    # Check if the user is logged in
    if not user.is_authenticated:
        raise ClientError("USER_HAS_TO_LOGIN")
    # Find the room they requested (by ID)
    try:
        users = User.objects.filter(game_room=room_id)
    except User.DoesNotExist:
        raise ClientError("USER_INVALID")
    return users

@database_sync_to_async
def add_player_to_room(room_id, user):
    """
    Tries to add a player to the room, checking permissions along the way.
    """
    # Check if the user is logged in
    if not user.is_authenticated:
        raise ClientError("USER_HAS_TO_LOGIN")
    # Find the room they requested (by ID)
    try:
        user.game_room = Room.objects.get(pk=room_id)
        user.ready = False # default to not being ready
        user.save()
    except User.DoesNotExist:
        raise ClientError("USER_INVALID")
    except Room.DoesNotExist:
        raise ClientError("ROOM_INVALID")
    return True

@database_sync_to_async
def remove_player_from_room(room_id, user):
    """
    Tries to remove a player from a room, checking permissions along the way.
    """
    # Check if the user is logged in
    if not user.is_authenticated:
        raise ClientError("USER_HAS_TO_LOGIN")
    # Find the room they requested (by ID)
    try:
        user.game_room = None
        user.save()
    except User.DoesNotExist:
        raise ClientError("USER_INVALID")
    except Room.DoesNotExist:
        raise ClientError("ROOM_INVALID")
    return True

@database_sync_to_async
def ready_player(user):
    """
    Tries to ready up player
    """
    try:
        user.ready = True
        user.save()
    except User.DoesNotExist:
        raise ClientError("Unknown Error readying player")
    return True