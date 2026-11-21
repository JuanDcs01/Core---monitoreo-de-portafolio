from django.contrib.auth.models import AbstractUser
from django.db import models

class Currency(models.TextChoices):
    DOP = 'DOP', 'RD$'
    EUR = 'EUR', '€'
    MXN = 'MXN', 'MX$'
    COP = 'COP', 'COL$'
    ARS = 'ARS', 'AR$'
    CLP = 'CLP', 'CL$'
    PEN = 'PEN', 'S/'
    BRL = 'BRL', 'R$'
    UYU = 'UYU', '$U'
    BOB = 'BOB', 'Bs.'
    PYG = 'PYG', '₲'
    CRC = 'CRC', '₡'
    GTQ = 'GTQ', 'Q'
    HNL = 'HNL', 'L'
    NIO = 'NIO', 'C$'
    PAB = 'PAB', 'B/.'
    VES = 'VES', 'Bs.'

class User(AbstractUser):

    email = models.EmailField(unique=True, blank=False, null=False)
    currency = models.CharField(max_length=5, choices=Currency.choices, default=Currency.DOP)

    def __str__(self):
        return f'usuario: {self.username}'