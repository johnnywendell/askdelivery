import uuid
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.test import TestCase, Client
from django.urls import reverse

from core.models import User, Usuario, Restaurante, Entregador
from orders.models import Order
from .models import Wallet, FundingRequest, WalletTransaction, DeliveryConfig
from .services import WalletService, DeliveryService


class WalletTests(TestCase):
    def setUp(self):
        self.owner = self.profile('rest', 'RESTAURANTE')
        self.driver = self.profile('driver', 'ENTREGADOR')
        self.other = self.profile('other', 'ENTREGADOR')
        self.restaurant = Restaurante.objects.create(usuario=self.owner, nome_fantasia='Restaurante',
            cnpj='test', latitude='-12.97', longitude='-38.50')
        self.courier = Entregador.objects.create(usuario=self.driver, cpf='test', tipo_veiculo='MOTO')
        self.stranger = Entregador.objects.create(usuario=self.other, cpf='other', tipo_veiculo='MOTO')
        self.admin = User.objects.create_user(username='admin', email='admin@example.test', is_superuser=True, is_staff=True)
        for profile, codename in [(self.owner, 'restaurante'), (self.driver, 'entregador'), (self.other, 'entregador')]:
            profile.user.user_permissions.add(Permission.objects.get(codename=codename))
        self.wallet = self.owner.wallet
        self.wallet = WalletService.depositar(self.wallet, '100.00')

    def profile(self, name, kind):
        user = User.objects.create_user(username=name, email=f'{name}@example.test', password='test')
        return Usuario.objects.create(user=user, tipo=kind)

    def order(self, **kwargs):
        values = dict(restaurante=self.restaurant, customer_name='Cliente teste', address='Destino',
            latitude='-12.97', longitude='-38.50', status='approved')
        values.update(kwargs)
        return Order.objects.create(**values)

    def funded_order(self):
        return DeliveryService.reserve(self.order())

    def assigned_order(self):
        order = self.funded_order()
        order.entregador = self.courier
        order.status = 'accepted'
        order.save()
        return order

    def test_wallet_created_for_all_profile_types(self):
        for kind in ['CLIENTE', 'RESTAURANTE', 'ENTREGADOR', 'ADMIN']:
            self.assertEqual(self.profile(kind, kind).wallet.saldo, 0)

    def test_invalid_money_rejected(self):
        for amount in ['0', '-10', 'NaN', 'Infinity', '1.001', 'invalid', '100000000']:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                WalletService.depositar(self.wallet, amount)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.saldo, 100)

    def test_stale_instance_cannot_overwrite_balance(self):
        stale = Wallet.objects.get(pk=self.wallet.pk)
        WalletService.depositar(self.wallet, 20)
        WalletService.depositar(stale, 10)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.saldo, 130)

    def test_insufficient_funds_leave_no_transaction(self):
        count = WalletTransaction.objects.count()
        with self.assertRaises(ValueError):
            WalletService.sacar(self.wallet, 101)
        self.assertEqual(WalletTransaction.objects.count(), count)

    def test_database_rejects_negative_balance(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Wallet.objects.filter(pk=self.wallet.pk).update(saldo=-1)

    def test_quote_and_snapshot(self):
        DeliveryConfig.objects.create(valor_base='8.00', valor_km='3.00')
        order = self.funded_order()
        self.assertEqual(order.delivery_fee, 8)
        self.assertEqual(order.delivery_distance_km, 0)
        DeliveryConfig.objects.update(valor_base=20)
        self.assertEqual(DeliveryService.reserve(order).delivery_fee, 8)

    def test_distance_calculation(self):
        order = self.order(latitude='-12.98')
        distance, base, per_km, fee = DeliveryService.quote(order)
        self.assertEqual(distance, Decimal('1.112'))
        self.assertEqual(fee, Decimal('7.22'))

    def test_missing_restaurant_coordinates_rejected(self):
        self.restaurant.latitude = None
        self.restaurant.save()
        with self.assertRaises(ValueError):
            DeliveryService.reserve(self.order())

    def test_reservation_is_idempotent(self):
        order = self.funded_order()
        DeliveryService.reserve(order)
        self.wallet.refresh_from_db()
        self.assertEqual((self.wallet.saldo, self.wallet.saldo_reservado), (95, 5))
        self.assertEqual(order.wallet_transactions.filter(tipo='RESERVE').count(), 1)

    def test_cancellation_releases_once(self):
        order = self.funded_order()
        for _ in range(2):
            DeliveryService.transition(order.pk, self.owner.user, 'canceled')
        self.wallet.refresh_from_db()
        self.assertEqual((self.wallet.saldo, self.wallet.saldo_reservado), (100, 0))
        self.assertEqual(order.wallet_transactions.filter(tipo='RELEASE').count(), 1)

    def test_delivery_pays_exactly_once(self):
        order = self.assigned_order()
        DeliveryService.transition(order.pk, self.driver.user, 'in_transit')
        for _ in range(2):
            DeliveryService.transition(order.pk, self.driver.user, 'delivered')
        self.wallet.refresh_from_db()
        self.driver.wallet.refresh_from_db()
        self.assertEqual((self.wallet.saldo, self.wallet.saldo_reservado, self.driver.wallet.saldo), (95, 0, 5))
        self.assertEqual(order.wallet_transactions.filter(tipo='CREDIT').count(), 1)
        self.assertEqual(order.wallet_transactions.filter(tipo='DELIVERY_PAYMENT').count(), 1)

    def test_cannot_cancel_after_start_or_pay_before_start(self):
        order = self.assigned_order()
        with self.assertRaises(ValueError):
            DeliveryService.transition(order.pk, self.driver.user, 'delivered')
        DeliveryService.transition(order.pk, self.driver.user, 'in_transit')
        with self.assertRaises(ValueError):
            DeliveryService.transition(order.pk, self.owner.user, 'canceled')

    def test_other_driver_cannot_move_order(self):
        with self.assertRaises(PermissionError):
            DeliveryService.transition(self.assigned_order().pk, self.other.user, 'in_transit')

    def test_failure_to_credit_rolls_back_payer_and_status(self):
        order = self.assigned_order()
        DeliveryService.transition(order.pk, self.driver.user, 'in_transit')
        original = WalletService._move
        def fail_credit(*args, **kwargs):
            if args[2] == 'CREDIT':
                raise ValueError('Simulated failure')
            return original(*args, **kwargs)
        with patch.object(WalletService, '_move', side_effect=fail_credit), self.assertRaises(ValueError):
            DeliveryService.transition(order.pk, self.driver.user, 'delivered')
        self.wallet.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.wallet.saldo_reservado, 5)
        self.assertEqual(order.status, 'in_transit')
        self.assertFalse(order.wallet_transactions.filter(tipo='DELIVERY_PAYMENT').exists())

    def test_deposit_pending_until_approved_and_duplicate_review_safe(self):
        req = WalletService.solicitar(self.wallet, 'deposit', 30)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.saldo, 100)
        for _ in range(2):
            WalletService.revisar(req.public_id, self.admin, True)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.saldo, 130)

    def test_rejected_deposit_does_not_credit(self):
        req = WalletService.solicitar(self.wallet, 'deposit', 30)
        WalletService.revisar(req.public_id, self.admin, False)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.saldo, 100)

    def test_withdrawal_reserves_and_rejection_releases_once(self):
        req = WalletService.solicitar(self.wallet, 'withdraw', 30)
        self.wallet.refresh_from_db()
        self.assertEqual((self.wallet.saldo, self.wallet.saldo_reservado), (70, 30))
        for _ in range(2):
            WalletService.revisar(req.public_id, self.admin, False)
        self.wallet.refresh_from_db()
        self.assertEqual((self.wallet.saldo, self.wallet.saldo_reservado), (100, 0))

    def test_withdrawal_approved_consumes_only_its_reservation(self):
        self.funded_order()
        req = WalletService.solicitar(self.wallet, 'withdraw', 30)
        WalletService.revisar(req.public_id, self.admin, True)
        self.wallet.refresh_from_db()
        self.assertEqual((self.wallet.saldo, self.wallet.saldo_reservado), (65, 5))

    def test_request_idempotency(self):
        key = uuid.uuid4()
        first = WalletService.solicitar(self.wallet, 'withdraw', 30, public_id=key)
        second = WalletService.solicitar(self.wallet, 'withdraw', 30, public_id=key)
        self.assertEqual(first.pk, second.pk)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.saldo, 70)

    def test_cannot_review_as_normal_user(self):
        req = WalletService.solicitar(self.wallet, 'deposit', 30)
        with self.assertRaises(ValueError):
            WalletService.revisar(req.public_id, self.owner.user, True)

    def test_dashboard_is_private_and_renders(self):
        self.client.force_login(self.driver.user)
        response = self.client.get(reverse('wallet:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wallet'].usuario_id, self.driver.pk)
        self.assertNotContains(response, 'Depósito confirmado')
        self.assertEqual(self.client.get(reverse('wallet:management')).status_code, 302)

    def test_admin_pages_render_without_profile(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('wallet:management')).status_code, 200)
        order = self.funded_order()
        self.assertEqual(self.client.get(reverse('orders:order_detail', args=[order.public_id])).status_code, 200)

    def test_request_view_validation_and_post(self):
        self.client.force_login(self.owner.user)
        url = reverse('wallet:dashboard')
        invalid = self.client.post(url, {'kind': 'withdraw', 'amount': '101', 'public_id': uuid.uuid4()})
        self.assertContains(invalid, 'Saldo insuficiente')
        response = self.client.post(url, {'kind': 'deposit', 'amount': '10', 'public_id': uuid.uuid4()})
        self.assertRedirects(response, url)
        self.assertEqual(FundingRequest.objects.count(), 1)

    def test_csrf_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner.user)
        self.assertEqual(client.post(reverse('wallet:dashboard'), {}).status_code, 403)

    def test_create_form_insufficient_balance_rolls_back_order(self):
        WalletService.sacar(self.wallet, 100)
        self.client.force_login(self.owner.user)
        response = self.client.post(reverse('orders:orders_criar'), {
            'customer_name': 'Teste', 'address': 'Destino', 'latitude': '-12.97', 'longitude': '-38.50'})
        self.assertContains(response, 'Saldo insuficiente')
        self.assertEqual(Order.objects.count(), 0)

    def test_create_api_uses_authenticated_restaurant_and_reserves(self):
        self.client.force_login(self.owner.user)
        response = self.client.post('/orders/orders/create', {
            'customer_name': 'Teste', 'address': 'Destino', 'latitude': '-12.97', 'longitude': '-38.50',
            'restaurante': 9999})
        self.assertEqual(response.status_code, 201, response.content)
        order = Order.objects.get()
        self.assertEqual(order.restaurante_id, self.restaurant.pk)
        self.assertEqual(order.payment_state, 'reserved')

    def test_legacy_order_acceptance_reserves_and_renders(self):
        order = self.order()
        self.client.force_login(self.driver.user)
        response = self.client.post(reverse('orders:accept_order', args=[order.pk]))
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.payment_state, 'reserved')
        self.assertEqual(order.entregador_id, self.courier.pk)
        self.assertEqual(self.client.get(reverse('orders:order_detail', args=[order.public_id])).status_code, 200)

    def test_unrelated_order_access_rejected(self):
        order = self.assigned_order()
        self.client.force_login(self.other.user)
        self.assertEqual(self.client.get(reverse('orders:order_detail', args=[order.public_id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('orders:order_start_delivery', args=[order.public_id])).status_code, 403)

    def test_destination_edit_rejected(self):
        order = self.funded_order()
        self.client.force_login(self.owner.user)
        response = self.client.post(reverse('orders:order_update', args=[order.public_id]), {
            'customer_name': 'Teste', 'address': 'Outro destino', 'latitude': '-12.98', 'longitude': '-38.50'})
        self.assertContains(response, 'Para alterar o destino')
        order.refresh_from_db()
        self.assertEqual(order.address, 'Destino')

    def test_quote_endpoint_does_not_reserve(self):
        self.client.force_login(self.owner.user)
        response = self.client.get(reverse('wallet:quote'), {'latitude': '-12.97', 'longitude': '-38.50'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['fee'], '5.00')
        self.wallet.refresh_from_db()
        self.assertEqual((self.wallet.saldo, self.wallet.saldo_reservado), (100, 0))
        self.assertEqual(self.client.get(reverse('wallet:quote'), {'latitude': 'NaN'}).status_code, 400)
        self.client.force_login(self.driver.user)
        self.assertEqual(self.client.get(reverse('wallet:quote')).status_code, 403)
