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


class CadastroApprovalTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='root', email='root@example.test', password='Admin-test-987!')

    def test_public_errors_highlight_fields_and_messages(self):
        response = self.client.post(reverse('core:solicitar_cadastro'), {'tipo': 'CLIENTE'})
        self.assertContains(response, 'field-error')
        self.assertContains(response, 'class="errorlist"')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'Este campo é obrigatório.')

    def test_admin_can_activate_approve_and_deactivate_each_role(self):
        from tempfile import TemporaryDirectory
        from django.test import override_settings
        for kind, route in (('CLIENTE', 'cliente_update'), ('RESTAURANTE', 'restaurante_update'), ('ENTREGADOR', 'entregador_update')):
            with self.subTest(kind=kind), TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
                self.client.logout()
                public_data = self.payload(kind)
                public_data['user-email'] = kind.lower() + '@example.test'
                self.client.post(reverse('core:solicitar_cadastro'), public_data)
                user = User.objects.get(email=public_data['user-email'])
                perfil = user.perfil
                subtype = getattr(perfil, kind.lower())
                url = reverse('core:' + route, args=[subtype.pk])
                # Campos extras não permitem que o próprio usuário ative a conta.
                self.client.force_login(user)
                self.assertNotEqual(self.client.post(url, {'is_active': 'on'}).status_code, 200)
                self.client.force_login(self.admin)
                self.assertContains(self.client.get(url), 'name="is_active"')
                data = {key.removeprefix('user-').removeprefix('dados-'): value
                        for key, value in public_data.items() if key.startswith(('user-', 'dados-'))}
                data.update(password='', confirm_password='', is_active='on')
                self.assertRedirects(self.client.post(url, data), reverse('core:usuario_list'))
                user.refresh_from_db()
                perfil.refresh_from_db()
                self.assertTrue(user.is_active)
                from django.contrib.auth import authenticate
                self.assertEqual(authenticate(email=user.email, password='Secure-pass-2846!'), user)
                self.assertTrue(perfil.ativo)
                self.assertFalse(perfil.cadastro_pendente)
                self.assertEqual(perfil.aprovado_por, self.admin)
                self.assertIsNotNone(perfil.aprovado_em)
                self.assertTrue(user.has_perm('core.' + kind.lower()))
                if kind == 'ENTREGADOR':
                    subtype.refresh_from_db()
                    self.assertTrue(subtype.aprovado)
                data.pop('is_active')
                self.assertRedirects(self.client.post(url, data), reverse('core:usuario_list'))
                user.refresh_from_db()
                perfil.refresh_from_db()
                self.assertFalse(user.is_active)
                self.assertFalse(perfil.ativo)
                self.assertFalse(self.client.login(email=user.email, password='Secure-pass-2846!'))

    def test_admin_gets_profile_and_can_edit_it(self):
        self.assertFalse(Usuario.objects.filter(user=self.admin).exists())
        self.client.force_login(self.admin)
        response = self.client.get(reverse('core:meu_perfil'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Usuario.objects.get(user=self.admin).tipo, 'ADMIN')
        response = self.client.post(reverse('core:meu_perfil'), {'first_name': 'Admin', 'last_name': 'Teste', 'email': self.admin.email, 'telefone': '123'})
        self.assertRedirects(response, reverse('core:meu_perfil'))
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.first_name, 'Admin')
        self.assertEqual(Usuario.objects.filter(user=self.admin).count(), 1)

    def payload(self, kind):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from io import BytesIO
        from PIL import Image
        image = BytesIO()
        Image.new('RGB', (1, 1)).save(image, format='PNG')
        data = {'tipo': kind, 'user-first_name': 'Teste', 'user-last_name': 'Cadastro',
                'user-email': 'novo@example.test', 'user-telefone': '71999999999',
                'user-password': 'Secure-pass-2846!', 'user-confirm_password': 'Secure-pass-2846!',
                'perfil-foto': SimpleUploadedFile('foto.png', image.getvalue(), content_type='image/png')}
        from .forms import cadastro_forms
        form = cadastro_forms(kind)[2]
        values = {'cpf': '12345678901', 'data_nascimento': '1990-01-01', 'sexo': 'NA',
                  'address': 'Rua Teste, 10', 'latitude': '-12.97', 'longitude': '-38.50',
                  'nome_fantasia': 'Cozinha Teste', 'razao_social': 'Cozinha Ltda', 'cnpj': '12345678000199',
                  'descricao': 'Refeições', 'telefone_comercial': '7133333333', 'taxa_entrega': '5',
                  'tempo_preparo_min': '30', 'cnh': '12345678900', 'tipo_veiculo': 'MOTO', 'placa': 'ABC1234'}
        for name in form.fields:
            if name in values:
                data['dados-' + name] = values[name]
        return data

    def test_each_role_stays_inactive_until_admin_approval(self):
        from tempfile import TemporaryDirectory
        from django.test import override_settings
        for kind in ('CLIENTE', 'RESTAURANTE', 'ENTREGADOR'):
            with self.subTest(kind=kind), TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
                self.client.logout()
                data = self.payload(kind)
                data['user-email'] = kind.lower() + '@example.test'
                response = self.client.post(reverse('core:solicitar_cadastro'), data)
                self.assertRedirects(response, reverse('core:login'))
                user = User.objects.get(email=data['user-email'])
                perfil = user.perfil
                self.assertFalse(user.is_active)
                self.assertFalse(perfil.ativo)
                self.assertTrue(perfil.cadastro_pendente)
                self.assertFalse(user.user_permissions.exists())
                self.assertFalse(self.client.login(email=user.email, password=data['user-password']))
                self.client.force_login(self.admin)
                self.assertContains(self.client.get(reverse('core:usuario_list')), user.email)
                url = reverse('core:aprovar_cadastro', args=[perfil.pk])
                self.assertEqual(self.client.get(url).status_code, 405)
                self.assertRedirects(self.client.post(url), reverse('core:usuario_list'))
                self.client.post(url)
                user.refresh_from_db()
                perfil.refresh_from_db()
                self.assertTrue(user.is_active)
                self.assertTrue(perfil.ativo)
                self.assertFalse(perfil.cadastro_pendente)
                self.assertEqual(perfil.aprovado_por, self.admin)
                self.assertTrue(user.has_perm('core.' + kind.lower()))
                self.client.logout()
                self.assertTrue(self.client.login(email=user.email, password=data['user-password']))

    def test_public_pages_and_required_fields(self):
        self.assertContains(self.client.get(reverse('core:login')), 'Solicitar cadastro')
        self.assertEqual(self.client.get(reverse('core:solicitar_cadastro')).status_code, 200)
        response = self.client.post(reverse('core:solicitar_cadastro'), {'tipo': 'CLIENTE'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(is_superuser=False).exists())
        self.assertEqual(self.client.post(reverse('core:solicitar_cadastro'), {'tipo': 'ADMIN'}).status_code, 400)

    def test_non_superuser_cannot_approve(self):
        user = User.objects.create_user(username='staff', email='staff@example.test', is_staff=True)
        perfil = Usuario.objects.create(user=user, tipo='ADMIN', cadastro_pendente=True)
        self.client.force_login(user)
        response = self.client.post(reverse('core:aprovar_cadastro', args=[perfil.pk]))
        self.assertEqual(response.status_code, 302)
        perfil.refresh_from_db()
        self.assertTrue(perfil.cadastro_pendente)

    def test_admin_can_create_order_for_selected_restaurant(self):
        from wallet.services import WalletService
        owner = User.objects.create_user(username='kitchen', email='kitchen@example.test')
        perfil = Usuario.objects.create(user=owner, tipo='RESTAURANTE')
        restaurant = Restaurante.objects.create(usuario=perfil, nome_fantasia='Cozinha', latitude=-12.97, longitude=-38.50)
        WalletService.depositar(perfil.wallet, 100)
        self.client.force_login(self.admin)
        url = reverse('orders:orders_criar')
        self.assertContains(self.client.get(url), 'Restaurante responsável')
        data = {'restaurante': restaurant.pk, 'customer_name': 'Cliente', 'customer_phone': '71999999999',
                'address': 'Rua Destino', 'latitude': '-12.97', 'longitude': '-38.50'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get()
        self.assertEqual(order.restaurante, restaurant)
        self.assertEqual(order.payment_state, 'reserved')
        self.assertEqual(self.client.get(reverse('wallet:quote'), {'restaurante': restaurant.pk, 'latitude': '-12.97', 'longitude': '-38.50'}).status_code, 200)
        data.pop('restaurante')
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertEqual(Order.objects.count(), 1)

    def test_registration_rejects_incomplete_invalid_and_duplicate_data(self):
        from tempfile import TemporaryDirectory
        from django.test import override_settings
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            for field, value in [('dados-cpf', ''), ('dados-latitude', '91'), ('user-confirm_password', 'different'), ('perfil-foto', '')]:
                data = self.payload('CLIENTE')
                data[field] = value
                self.assertEqual(self.client.post(reverse('core:solicitar_cadastro'), data).status_code, 200)
                self.assertFalse(User.objects.filter(email='novo@example.test').exists())
            data = self.payload('CLIENTE')
            data['user-email'] = self.admin.email.upper()
            self.assertEqual(self.client.post(reverse('core:solicitar_cadastro'), data).status_code, 200)
            self.assertEqual(User.objects.count(), 1)

    def test_public_registration_and_approval_require_csrf(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('core:solicitar_cadastro'), {'tipo': 'CLIENTE'}).status_code, 403)
        client.force_login(self.admin)
        self.assertEqual(client.post(reverse('core:aprovar_cadastro', args=[1])).status_code, 403)

    def test_admin_api_creation_reserves_selected_restaurant_wallet(self):
        from wallet.services import WalletService
        user = User.objects.create_user(username='api-kitchen', email='api-kitchen@example.test')
        perfil = Usuario.objects.create(user=user, tipo='RESTAURANTE')
        restaurant = Restaurante.objects.create(usuario=perfil, nome_fantasia='API', latitude=0, longitude=0)
        WalletService.depositar(perfil.wallet, 50)
        self.client.force_login(self.admin)
        response = self.client.post('/orders/orders/create', {'restaurante': restaurant.pk, 'customer_name': 'Teste',
                                  'customer_phone': '123', 'address': 'Destino', 'latitude': '0', 'longitude': '0'})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Order.objects.get().restaurante, restaurant)
