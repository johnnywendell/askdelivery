from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from core.models import User, Usuario, Restaurante, Entregador
from orders.models import Order
from wallet.models import FundingRequest, WalletTransaction


class IndexDashboardTests(TestCase):
    def setUp(self):
        self.restaurant_profile = self.profile('restaurant', 'RESTAURANTE')
        self.restaurant = Restaurante.objects.create(usuario=self.restaurant_profile, nome_fantasia='Minha cozinha', cnpj='test')
        self.other_profile = self.profile('other', 'RESTAURANTE')
        self.other_restaurant = Restaurante.objects.create(usuario=self.other_profile, nome_fantasia='Outra cozinha', cnpj='other')
        self.driver_profile = self.profile('driver', 'ENTREGADOR')
        self.driver = Entregador.objects.create(usuario=self.driver_profile, cpf='test', tipo_veiculo='MOTO')
        self.own_order = self.order(self.restaurant, entregador=self.driver, status='accepted')
        self.foreign_order = self.order(self.other_restaurant)
        self.restaurant_profile.wallet.saldo = Decimal('123.45')
        self.restaurant_profile.wallet.save()
        FundingRequest.objects.create(wallet=self.other_profile.wallet, kind='deposit', amount=90)

    def profile(self, name, kind):
        user = User.objects.create_user(username=name, email=f'{name}@example.test')
        return Usuario.objects.create(user=user, tipo=kind)

    def order(self, restaurant, **kwargs):
        return Order.objects.create(restaurante=restaurant, customer_name='Teste', address='Destino', latitude=0, longitude=0, **kwargs)

    def dashboard(self, user):
        self.client.force_login(user)
        response = self.client.get(reverse('core:index'))
        self.assertEqual(response.status_code, 200)
        return response

    def test_restaurant_only_sees_own_orders_and_wallet(self):
        response = self.dashboard(self.restaurant_profile.user)
        self.assertEqual(response.context['dashboard_role'], 'restaurant')
        self.assertEqual(list(response.context['active_orders']), [self.own_order])
        self.assertEqual(response.context['wallet'].saldo, Decimal('123.45'))
        self.assertEqual(response.context['pending_count'], 0)
        self.assertNotContains(response, 'Outra cozinha')
        self.assertContains(response, 'Criar pedido')

    def test_driver_only_sees_assigned_orders_and_credited_earnings(self):
        WalletTransaction.objects.create(wallet=self.driver_profile.wallet, tipo='DELIVERY_PAYMENT', valor=12)
        WalletTransaction.objects.create(wallet=self.other_profile.wallet, tipo='DELIVERY_PAYMENT', valor=99)
        response = self.dashboard(self.driver_profile.user)
        self.assertEqual(response.context['dashboard_role'], 'driver')
        self.assertEqual(list(response.context['active_orders']), [self.own_order])
        gains = next(item for item in response.context['metrics'] if item['label'] == 'Ganhos de hoje')
        self.assertEqual(gains['value'], Decimal('12'))
        self.assertEqual(response.context['available_orders'], 1)
        self.assertContains(response, 'Buscar corridas')

    def test_admin_without_profile_sees_global_summary(self):
        admin = User.objects.create_user(username='admin', email='admin@example.test', is_superuser=True)
        response = self.dashboard(admin)
        self.assertEqual(response.context['dashboard_role'], 'admin')
        self.assertEqual(len(response.context['active_orders']), 2)
        self.assertEqual(len(response.context['pending_requests']), 1)
        self.assertContains(response, 'Gerenciar carteiras')

    def test_admin_label_and_staff_do_not_grant_global_access(self):
        profile = self.profile('staff', 'ADMIN')
        profile.user.is_staff = True
        profile.user.save()
        response = self.dashboard(profile.user)
        self.assertEqual(response.context['dashboard_role'], 'basic')
        self.assertNotIn('pending_requests', response.context)
        self.assertNotContains(response, 'Outra cozinha')

    def test_client_and_missing_profiles_have_basic_page(self):
        for user in [self.profile('customer', 'CLIENTE').user,
                     User.objects.create_user(username='bare', email='bare@example.test')]:
            response = self.dashboard(user)
            self.assertEqual(response.context['dashboard_role'], 'basic')
            self.assertNotContains(response, 'Minha cozinha')

    def test_incomplete_and_empty_profiles_render(self):
        response = self.dashboard(self.profile('incomplete', 'ENTREGADOR').user)
        self.assertContains(response, 'Cadastro incompleto')
        self.own_order.delete()
        response = self.dashboard(self.driver_profile.user)
        self.assertContains(response, 'Nenhuma entrega em andamento')

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(reverse('core:index'))
        self.assertRedirects(response, reverse('core:login'), fetch_redirect_response=False)
