from django.db import models
from users.models import User 

# Create your models here.

class Holding(models.Model):

    name = models.CharField(max_length=100, unique=True)
    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    type = models.CharField(max_length=20)

    def __str__(self):
        return self.name

class UserHolding(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    holding = models.ForeignKey(Holding, on_delete=models.CASCADE)

    class Meta:

        constraints = [
            models.UniqueConstraint(fields=['user', 'holding'], name='unique_user_holding')
        ]

class WatchList(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_user_name'
            )
        ]

class HoldingList(models.Model):

    watch_list = models.ForeignKey(WatchList, on_delete=models.CASCADE)
    holding = models.ForeignKey(Holding, on_delete=models.CASCADE)

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=['watch_list', 'holding'],
                name='unique_watch_list_holding'
            )
        ]

class TransactionType(models.TextChoices):

    DEPOSIT = 'D', 'Depósito'
    WITHDRAW = 'W', 'Retiro'

class WalletTransaction(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=1, choices=TransactionType.choices)
    net_amount = models.DecimalField()
    commission = models.DecimalField()
    date = models.DateField()

    @property
    def total(self):
        return self.net_amount + self.commission

