from django.db import models
from django.contrib.auth.models import User

class Destino(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome


class Lancamento(models.Model):
    STATUS_CHOICES = [
        ('liberado', 'Liberado'),
        ('aguardando', 'Aguardando'),
        ('finalizado', 'Finalizado'),
    ]

    po = models.CharField(max_length=10)
    destino = models.ForeignKey(Destino, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    observacao = models.TextField(blank=True)
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.po} - {self.destino}"


class ConfiguracaoDashboard(models.Model):
    TEMA_CHOICES = [
        ('claro', 'Claro'),
        ('escuro', 'Escuro'),
        ('azul', 'Azul'),
    ]

    tema = models.CharField(max_length=20, choices=TEMA_CHOICES, default='claro')

    def __str__(self):
        return f"Tema atual: {self.tema}"
