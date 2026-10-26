from django.db import models
from core.models import Usuario
from orders.models import Order
import uuid


class DeliveryConfig(models.Model):
    valor_base = models.DecimalField(max_digits=10,decimal_places=2,default=5)
    valor_km = models.DecimalField(max_digits=10,decimal_places=2,default=2)

class Wallet(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='wallet')
    saldo = models.DecimalField(verbose_name='Saldo', max_digits=12, decimal_places=2, default=0)
    saldo_reservado = models.DecimalField(verbose_name='Saldo Reservado', max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    class Meta:
        verbose_name = 'Carteira'
        verbose_name_plural = 'Carteiras'

    def __str__(self):
        return f'{self.usuario} - R$ {self.saldo}'

class WalletTransaction(models.Model):
    class Tipo(models.TextChoices):
        DEPOSIT = ('DEPOSIT', 'Depósito')
        WITHDRAW = ('WITHDRAW', 'Saque')
        CREDIT = ('CREDIT', 'Crédito')
        DEBIT = ('DEBIT', 'Débito')
        RESERVE = ('RESERVE', 'Reserva')
        RELEASE = ('RELEASE', 'Liberação')
        DELIVERY_PAYMENT = ('DELIVERY_PAYMENT', 'Pagamento de Entrega')

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transacoes')
    pedido = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True, related_name='wallet_transactions')
    valor = models.DecimalField(verbose_name='Valor', max_digits=12, decimal_places=2)
    tipo = models.CharField(verbose_name='Tipo', max_length=30, choices=Tipo.choices)
    saldo_anterior = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_posterior = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descricao = models.TextField(verbose_name='Descrição', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    class Meta:
        verbose_name = 'Transação'
        verbose_name_plural = 'Transações'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_tipo_display()} - R$ {self.valor}'