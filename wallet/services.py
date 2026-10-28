"""Movimentos internos; confirmação bancária é feita pelo administrador."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from math import radians, sin, cos, asin, sqrt, isfinite

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Wallet, WalletTransaction, DeliveryConfig, FundingRequest


def money(value):
    try:
        value = Decimal(str(value))
        if not value.is_finite() or value <= 0 or value > Decimal('99999999.99'):
            raise ValueError
        if value != value.quantize(Decimal('.01')):
            raise ValueError
        return value.quantize(Decimal('.01'))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError('Informe um valor positivo com até duas casas decimais.')


class WalletService:
    @staticmethod
    def _move(wallet, valor, tipo, available, reserved=0, pedido=None, descricao=''):
        """Use somente dentro de atomic. UPDATE condicional protege também no SQLite."""
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        before = wallet.saldo
        query = Wallet.objects.filter(pk=wallet.pk)
        if available > 0:
            query = query.filter(saldo__lte=Decimal('9999999999.99') - available)
        if reserved > 0:
            query = query.filter(saldo_reservado__lte=Decimal('9999999999.99') - reserved)
        if available < 0:
            query = query.filter(saldo__gte=-available)
        if reserved < 0:
            query = query.filter(saldo_reservado__gte=-reserved)
        if not query.update(saldo=F('saldo') + available,
                            saldo_reservado=F('saldo_reservado') + reserved,
                            updated_at=timezone.now()):
            raise ValueError('Saldo insuficiente para esta operação.')
        wallet.refresh_from_db()
        WalletTransaction.objects.create(wallet=wallet, pedido=pedido, valor=valor,
            tipo=tipo, saldo_anterior=before, saldo_posterior=wallet.saldo, descricao=descricao)
        return wallet

    @staticmethod
    @transaction.atomic
    def depositar(wallet, valor, descricao='Depósito confirmado'):
        valor = money(valor)
        return WalletService._move(wallet, valor, 'DEPOSIT', valor, descricao=descricao)

    @staticmethod
    @transaction.atomic
    def sacar(wallet, valor, descricao='Saque'):
        valor = money(valor)
        return WalletService._move(wallet, valor, 'WITHDRAW', -valor, descricao=descricao)

    @staticmethod
    @transaction.atomic
    def reservar_saldo(wallet, valor, pedido=None):
        if pedido is not None:
            raise ValueError('Use DeliveryService.reserve para reservar pedidos.')
        valor = money(valor)
        return WalletService._move(wallet, valor, 'RESERVE', -valor, valor, descricao='Reserva para saque')

    @staticmethod
    @transaction.atomic
    def solicitar(wallet, kind, amount, note='', public_id=None):
        amount = money(amount)
        if kind not in FundingRequest.Kind.values:
            raise ValueError('Tipo de solicitação inválido.')
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        existing = FundingRequest.objects.filter(public_id=public_id).first()
        if existing:
            if existing.wallet_id != wallet.pk or existing.kind != kind or existing.amount != amount:
                raise ValueError('Identificador de solicitação já utilizado.')
            return existing
        if kind == FundingRequest.Kind.WITHDRAW:
            WalletService.reservar_saldo(wallet, amount)
        return FundingRequest.objects.create(wallet=wallet, kind=kind, amount=amount,
            note=note, **({'public_id': public_id} if public_id else {}))

    @staticmethod
    @transaction.atomic
    def revisar(public_id, admin, approve, note=''):
        if not admin.is_superuser:
            raise ValueError('Apenas administradores podem confirmar movimentações.')
        req = FundingRequest.objects.select_for_update().get(public_id=public_id)
        if req.status != FundingRequest.Status.PENDING:
            return req
        if req.kind == FundingRequest.Kind.DEPOSIT:
            if approve:
                WalletService.depositar(req.wallet, req.amount, f'Depósito confirmado · {req.public_id}')
        elif approve:
            WalletService._move(req.wallet, req.amount, 'WITHDRAW', Decimal(0), -req.amount,
                                descricao=f'Saque confirmado · {req.public_id}')
        else:
            WalletService._move(req.wallet, req.amount, 'RELEASE', req.amount, -req.amount,
                                descricao=f'Saque recusado · {req.public_id}')
        req.status = FundingRequest.Status.APPROVED if approve else FundingRequest.Status.REJECTED
        req.reviewed_by = admin
        req.reviewed_at = timezone.now()
        req.review_note = note
        req.save()
        return req


class DeliveryService:
    @staticmethod
    def quote(order):
        config = DeliveryConfig.objects.order_by('pk').first()
        base = config.valor_base if config else Decimal('5.00')
        per_km = config.valor_km if config else Decimal('2.00')
        if base <= 0 or per_km < 0:
            raise ValueError('Configure uma tarifa de entrega válida.')
        try:
            lat1, lon1, lat2, lon2 = map(float, (order.restaurante.latitude,
                order.restaurante.longitude, order.latitude, order.longitude))
            if not all(isfinite(v) for v in (lat1, lon1, lat2, lon2)) or not (
                -90 <= lat1 <= 90 and -90 <= lat2 <= 90 and -180 <= lon1 <= 180 and -180 <= lon2 <= 180):
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError('Cadastre coordenadas válidas do restaurante e do destino para calcular o frete.')
        a, b = radians(lat1), radians(lat2)
        h = sin((b-a)/2)**2 + cos(a)*cos(b)*sin(radians(lon2-lon1)/2)**2
        distance = Decimal(str(6371 * 2 * asin(sqrt(min(1, max(0, h)))))).quantize(Decimal('.001'), rounding=ROUND_HALF_UP)
        fee = (base + distance * per_km).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        money(fee)
        return distance, base, per_km, fee

    @staticmethod
    @transaction.atomic
    def reserve(order):
        from orders.models import Order
        order = Order.objects.select_for_update().select_related('restaurante__usuario').get(pk=order.pk)
        if order.payment_state == 'reserved':
            return order
        if order.payment_state != 'unfunded' or order.status in ('delivered', 'canceled'):
            raise ValueError('Este pedido não pode receber uma reserva.')
        distance, base, per_km, fee = DeliveryService.quote(order)
        wallet, _ = Wallet.objects.get_or_create(usuario=order.restaurante.usuario)
        WalletService._move(wallet, fee, 'RESERVE', -fee, fee, pedido=order,
                            descricao='Reserva de frete')
        order.delivery_distance_km, order.delivery_base, order.delivery_per_km, order.delivery_fee = distance, base, per_km, fee
        order.payment_state = 'reserved'
        order.save(update_fields=['delivery_distance_km', 'delivery_base', 'delivery_per_km', 'delivery_fee', 'payment_state'])
        return order

    @staticmethod
    @transaction.atomic
    def transition(order_id, actor, target):
        from orders.models import Order
        order = Order.objects.select_for_update().select_related('restaurante__usuario', 'entregador__usuario').get(pk=order_id)
        profile = getattr(actor, 'perfil', None)
        if target == 'canceled':
            authorized = profile and profile.pk == order.restaurante.usuario_id
        else:
            authorized = profile and order.entregador_id and profile.pk == order.entregador.usuario_id
        if not authorized:
            raise PermissionError('Você não pode alterar este pedido.')
        if order.status == target:
            return order
        allowed = {'in_transit': ['accepted', 'picking'], 'delivered': ['in_transit'],
                   'canceled': ['created', 'approved', 'accepted', 'picking']}
        if order.status not in allowed.get(target, []):
            raise ValueError('Esta alteração não é permitida no status atual.')
        payer, _ = Wallet.objects.get_or_create(usuario=order.restaurante.usuario)
        if target == 'canceled' and order.payment_state == 'reserved':
            WalletService._move(payer, order.delivery_fee, 'RELEASE', order.delivery_fee,
                -order.delivery_fee, pedido=order, descricao='Frete devolvido por cancelamento')
            order.payment_state = 'released'
        if target == 'delivered':
            if order.payment_state == 'unfunded':
                order = DeliveryService.reserve(order)
            if order.payment_state != 'reserved':
                raise ValueError('Pedido sem reserva para pagamento.')
            receiver, _ = Wallet.objects.get_or_create(usuario=order.entregador.usuario)
            if payer.pk == receiver.pk:
                raise ValueError('Restaurante e entregador precisam de carteiras distintas.')
            # Ordem consistente para bloquear as duas carteiras em bancos com row locks.
            list(Wallet.objects.select_for_update().filter(pk__in=[payer.pk, receiver.pk]).order_by('pk'))
            WalletService._move(payer, order.delivery_fee, 'DELIVERY_PAYMENT', Decimal(0),
                -order.delivery_fee, pedido=order, descricao='Pagamento de entrega')
            WalletService._move(receiver, order.delivery_fee, 'CREDIT', order.delivery_fee,
                pedido=order, descricao='Recebimento de entrega')
            order.payment_state = 'paid'
        order.status = target
        order.save(update_fields=['status', 'payment_state', 'updated_at'])
        return order
