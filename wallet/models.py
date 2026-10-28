from django.db import models
from core.models import Usuario
from orders.models import Order
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class DeliveryConfig(models.Model):
    valor_base = models.DecimalField(max_digits=10,decimal_places=2,default=5, validators=[MinValueValidator(Decimal('0.01'))])
    valor_km = models.DecimalField(max_digits=10,decimal_places=2,default=2, validators=[MinValueValidator(Decimal('0'))])

    def __str__(self):
        return f'Frete: R$ {self.valor_base} + R$ {self.valor_km}/km'

class Wallet(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.PROTECT, related_name='wallet')
    saldo = models.DecimalField(verbose_name='Saldo', max_digits=12, decimal_places=2, default=0)
    saldo_reservado = models.DecimalField(verbose_name='Saldo Reservado', max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(saldo__gte=0), name='wallet_balance_nonnegative'),
            models.CheckConstraint(condition=models.Q(saldo_reservado__gte=0), name='wallet_reserved_nonnegative'),
        ]
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

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='transacoes')
    pedido = models.ForeignKey(Order, on_delete=models.PROTECT, blank=True, null=True, related_name='wallet_transactions')
    valor = models.DecimalField(verbose_name='Valor', max_digits=12, decimal_places=2)
    tipo = models.CharField(verbose_name='Tipo', max_length=30, choices=Tipo.choices)
    saldo_anterior = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_posterior = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descricao = models.TextField(verbose_name='Descrição', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(valor__gt=0), name='wallet_transaction_positive'),
            models.UniqueConstraint(fields=['wallet', 'pedido', 'tipo'], name='wallet_order_movement_unique'),
        ]
        verbose_name = 'Transação'
        verbose_name_plural = 'Transações'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_tipo_display()} - R$ {self.valor}'

class FundingRequest(models.Model):
    class Kind(models.TextChoices):
        DEPOSIT = 'deposit', 'Depósito'
        WITHDRAW = 'withdraw', 'Saque'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        APPROVED = 'approved', 'Confirmada'
        REJECTED = 'rejected', 'Recusada'

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='solicitacoes')
    kind = models.CharField(max_length=10, choices=Kind.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    note = models.CharField(max_length=250, blank=True)
    review_note = models.CharField(max_length=250, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='funding_amount_positive')]
