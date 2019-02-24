from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    item = models.CharField(max_length=30, blank=True, null=True)
    eliminated = models.BooleanField(default=False)
    game_room = models.ForeignKey(
        'Room',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )

    target_player = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )

    ready = models.BooleanField(default=False)


class Room(models.Model):
    """
    A room for people to chat in.
    """

    # Room title
    title = models.CharField(max_length=255)

    # If only "staff" users are allowed (is_staff on django's User)
    staff_only = models.BooleanField(default=False)

    status = models.IntegerField(default=0)

    def __str__(self):
        return self.title

    @property
    def group_name(self):
        """
        Returns the Channels Group name that sockets should subscribe to to get sent
        messages as they are generated.
        """
        return "room-%s" % self.id
