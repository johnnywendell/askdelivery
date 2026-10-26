from decimal import Decimal
from django.db import transaction
from wallet.models import Wallet
from wallet.models import WalletTransaction


class WalletService:
    @staticmethod
    @transaction.atomic
    def depositar(wallet, valor, descricao='Depósito'):
        valor = Decimal(valor)
        saldo_anterior = wallet.saldo
        wallet.saldo += valor
        wallet.save(
            update_fields=['saldo']
        )
        WalletTransaction.objects.create(
            wallet=wallet,
            valor=valor,
            tipo=WalletTransaction.Tipo.DEPOSIT,
            descricao=descricao,
            saldo_anterior=saldo_anterior,
            saldo_posterior=wallet.saldo,
        )
        return wallet
    @staticmethod
    @transaction.atomic
    def sacar(wallet, valor, descricao='Saque'):
        valor = Decimal(valor)
        if wallet.saldo < valor:
            raise ValueError(
                'Saldo insuficiente.'
            )
        saldo_anterior = wallet.saldo
        wallet.saldo -= valor
        wallet.save(
            update_fields=['saldo']
        )
        WalletTransaction.objects.create(
            wallet=wallet,
            valor=valor,
            tipo=WalletTransaction.Tipo.WITHDRAW,
            descricao=descricao,
            saldo_anterior=saldo_anterior,
            saldo_posterior=wallet.saldo,
        )
        return wallet
    @staticmethod
    @transaction.atomic
    def reservar_saldo(wallet, valor, pedido=None):
        valor = Decimal(valor)
        if wallet.saldo < valor:
            raise ValueError(
                'Saldo insuficiente.'
            )
        saldo_anterior = wallet.saldo
        wallet.saldo -= valor
        wallet.saldo_reservado += valor
        wallet.save(
            update_fields=[
                'saldo',
                'saldo_reservado'
            ]
        )
        WalletTransaction.objects.create(
            wallet=wallet,
            pedido=pedido,
            valor=valor,
            tipo=WalletTransaction.Tipo.RESERVE,
            descricao='Reserva de saldo para entrega',
            saldo_anterior=saldo_anterior,
            saldo_posterior=wallet.saldo,
        )
        return wallet

    @staticmethod
    @transaction.atomic
    def liberar_reserva(wallet, valor, pedido=None):
        valor = Decimal(valor)
        if wallet.saldo_reservado < valor:
            raise ValueError(
                'Saldo reservado insuficiente.'
            )
        saldo_anterior = wallet.saldo
        wallet.saldo += valor
        wallet.saldo_reservado -= valor
        wallet.save(
            update_fields=[
                'saldo',
                'saldo_reservado'
            ]
        )
        WalletTransaction.objects.create(
            wallet=wallet,
            pedido=pedido,
            valor=valor,
            tipo=WalletTransaction.Tipo.RELEASE,
            descricao='Liberação de reserva',
            saldo_anterior=saldo_anterior,
            saldo_posterior=wallet.saldo,
        )
        return wallet
    @staticmethod
    @transaction.atomic
    def pagar_entregador(wallet_restaurante,wallet_entregador,valor,pedido=None):
        valor = Decimal(valor)
        if wallet_restaurante.saldo_reservado < valor:
            raise ValueError(
                'Saldo reservado insuficiente.'
            )
        #
        # RESTAURANTE
        #
        saldo_anterior_rest = wallet_restaurante.saldo
        wallet_restaurante.saldo_reservado -= valor
        wallet_restaurante.save(
            update_fields=[
                'saldo_reservado'
            ]
        )
        WalletTransaction.objects.create(
            wallet=wallet_restaurante,
            pedido=pedido,
            valor=valor,
            tipo=WalletTransaction.Tipo.DELIVERY_PAYMENT,
            descricao='Pagamento de entrega',
            saldo_anterior=saldo_anterior_rest,
            saldo_posterior=wallet_restaurante.saldo,
        )
        #
        # ENTREGADOR
        #
        saldo_anterior_ent = wallet_entregador.saldo
        wallet_entregador.saldo += valor
        wallet_entregador.save(
            update_fields=[
                'saldo'
            ]
        )
        WalletTransaction.objects.create(
            wallet=wallet_entregador,
            pedido=pedido,
            valor=valor,
            tipo=WalletTransaction.Tipo.CREDIT,
            descricao='Recebimento de entrega',
            saldo_anterior=saldo_anterior_ent,
            saldo_posterior=wallet_entregador.saldo,
        )
        return True