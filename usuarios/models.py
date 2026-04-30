# usuarios/models.py
from django.db import models
from django.contrib.auth.models import User

class Filial(models.Model):
    IBIPORA = 'ibipora'
    PARANAGUA = 'paranagua'
    RONDONOPOLIS = 'rondonopolis'
    
    CODIGOS_FILIAL = [
        (IBIPORA, 'Ibiporã'),
        (PARANAGUA, 'Paranaguá'),
        (RONDONOPOLIS, 'Rondonópolis'),
    ]
    
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, choices=CODIGOS_FILIAL, unique=True)
    app_django = models.CharField(max_length=50, default='core')
    url_inicial = models.CharField(max_length=100, default='/')
    ativa = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Filiais"
    
    def __str__(self):
        return f"{self.nome} ({self.codigo})"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # ADICIONE related_name ÚNICOS para evitar conflito
    filiais = models.ManyToManyField(Filial, blank=True, related_name='usuarios_com_acesso')
    filial_selecionada = models.ForeignKey(Filial, on_delete=models.SET_NULL, 
                                         null=True, blank=True, 
                                         related_name='usuarios_selecionados')
    
    def __str__(self):
        return f"{self.user.username}"