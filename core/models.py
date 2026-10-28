from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import os
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

def user_directory_path(instance, filename):
    extension = os.path.splitext(filename)[1]
    return 'media/imagens/usuarios/fotos_perfil/{0}_{1}{2}'.format(instance.user.username, instance.user.id, extension)

class User(AbstractUser):
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

TIPO = (
    ('CLIENTE', 'CLIENTE'),
    ('RESTAURANTE', 'RESTAURANTE'),
    ('ENTREGADOR', 'ENTREGADOR'),
    ('ADMIN', 'ADMIN'),
)
SEXO = (
    ('M', 'MASCULINO'),
    ('F', 'FEMININO'),
    ('NA', 'NÃO INFORMAR'),
)

class Usuario(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil'
    )

    tipo = models.CharField(max_length=20, choices=TIPO)

    cadastro_pendente = models.BooleanField(default=False)
    aprovado_em = models.DateTimeField(null=True, blank=True)
    aprovado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cadastros_aprovados',
    )

    foto = models.ImageField(
        upload_to=user_directory_path,
        blank=True,
        null=True
    )

    telefone_verificado = models.BooleanField(default=False)
    email_verificado = models.BooleanField(default=False)

    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    class Meta:
        permissions = (
            ("cliente", "Permissão de cliente"),
            ("entregador", "Permissão de entregador"),
            ("restaurante", "Permissão de restaurante"),
        )

    def __str__(self):
        return self.user.get_full_name() or self.user.email
    
class Cliente(models.Model):
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='cliente'
    )

    cpf = models.CharField(max_length=14, blank=True, null=True)
    data_nascimento = models.DateField(blank=True, null=True)
    sexo = models.CharField(max_length=20, choices=SEXO, blank=True, null=True)
    aceita_marketing = models.BooleanField(default=False)

    address = models.CharField(max_length=300)
    latitude = models.DecimalField(max_digits=15, decimal_places=10, null=True, blank=True)
    longitude = models.DecimalField(max_digits=15, decimal_places=10, null=True, blank=True)

    def __str__(self):
        return f'Cliente - {self.usuario}'

class Restaurante(models.Model):
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='restaurante'
    )

    nome_fantasia = models.CharField(max_length=200)
    razao_social = models.CharField(max_length=200, blank=True)
    cnpj = models.CharField(max_length=18)

    descricao = models.TextField(blank=True)

    telefone_comercial = models.CharField(max_length=20)

    aberto = models.BooleanField(default=False)

    taxa_entrega = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    tempo_preparo_min = models.IntegerField(default=30)

    address = models.CharField(max_length=300)
    latitude = models.DecimalField(max_digits=15, decimal_places=10, null=True, blank=True)
    longitude = models.DecimalField(max_digits=15, decimal_places=10, null=True, blank=True)

    aceita_retirada = models.BooleanField(default=True)

    def __str__(self):
        return self.nome_fantasia
    
class HorarioFuncionamento(models.Model):
    DIA = (
        (0, 'Segunda'),
        (1, 'Terça'),
        (2, 'Quarta'),
        (3, 'Quinta'),
        (4, 'Sexta'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    )

    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        related_name='horarios'
    )

    dia_semana = models.IntegerField(choices=DIA)

    hora_abertura = models.TimeField()
    hora_fechamento = models.TimeField()

    fechado = models.BooleanField(default=False)


TIPO_VEICULO = (
    ('MOTO', 'Moto'),
    ('CARRO', 'Carro'),
    ('BICICLETA', 'Bicicleta'),
)

STATUS = (
    ('OFFLINE', 'Offline'),
    ('ONLINE', 'Online'),
    ('OCUPADO', 'Ocupado'),
)

class Entregador(models.Model):
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='entregador'
    )

    cpf = models.CharField(max_length=14)
    cnh = models.CharField(max_length=20, blank=True)
    data_nascimento = models.DateField(blank=True, null=True)
    sexo = models.CharField(max_length=20, choices=SEXO, blank=True, null=True)
    
    tipo_veiculo = models.CharField(max_length=20, choices=TIPO_VEICULO)
    placa = models.CharField(max_length=10, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default='OFFLINE'
    )

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    ultima_localizacao = models.DateTimeField(null=True, blank=True)

    disponivel = models.BooleanField(default=False)

    aprovado = models.BooleanField(default=False)

    def __str__(self):
        return f'Entregador - {self.usuario}'
    
class DocumentoEntregador(models.Model):
    TIPO_DOC = (
        ('CNH', 'CNH'),
        ('CRLV', 'CRLV'),
        ('SELFIE', 'SELFIE'),
    )

    entregador = models.ForeignKey(
        Entregador,
        on_delete=models.CASCADE,
        related_name='documentos'
    )

    tipo = models.CharField(max_length=20, choices=TIPO_DOC)
    arquivo = models.FileField(upload_to='documentos_entregador/')

    aprovado = models.BooleanField(default=False)








