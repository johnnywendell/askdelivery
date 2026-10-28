"""Dados da página inicial, sempre limitados ao perfil autenticado."""
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from core.models import Entregador, Restaurante, Usuario
from orders.models import Order
from wallet.models import FundingRequest, Wallet, WalletTransaction


ACTIVE = ['created', 'approved', 'accepted', 'picking', 'in_transit']


def dashboard_context(user):
    now = timezone.localtime()
    today = now.date()
    profile = getattr(user, 'perfil', None)
    context = dict(page_title='Início', updated_at=now, profile=profile,
                   dashboard_role='basic', metrics=[], shortcuts=[], notices=[])

    def metric(label, value, hint, money=False):
        context['metrics'].append(dict(label=label, value=value, hint=hint, money=money))

    def shortcut(label, url, icon):
        context['shortcuts'].append(dict(label=label, url=url, icon=icon))

    orders = Order.objects.select_related('restaurante', 'entregador__usuario__user')
    if user.is_superuser:
        context.update(dashboard_role='admin', heading='Visão geral da operação',
                       subtitle='Pedidos, pessoas e movimentações que precisam da sua atenção.')
        totals = Wallet.objects.aggregate(available=Sum('saldo'), reserved=Sum('saldo_reservado'))
        pending = FundingRequest.objects.filter(status=FundingRequest.Status.PENDING)
        metric('Pedidos de hoje', orders.filter(created_at__date=today).count(), 'Criados hoje')
        metric('Entregas em andamento', orders.filter(status__in=ACTIVE).count(), 'Todos os restaurantes')
        metric('Saldo nas carteiras', totals['available'] or 0, 'Soma dos saldos disponíveis; não é receita', True)
        metric('Valores reservados', totals['reserved'] or 0, 'Reservas de fretes e saques', True)
        metric('Solicitações pendentes', pending.count(), 'Depósitos e saques aguardando análise')
        metric('Entregadores online', Entregador.objects.filter(status='ONLINE', disponivel=True, aprovado=True, usuario__ativo=True, usuario__user__is_active=True).count(), 'Aprovados e disponíveis')
        context['pending_requests'] = pending.select_related('wallet__usuario__user')[:5]
        context['people'] = Usuario.objects.aggregate(
            restaurants=Count('pk', filter=Q(tipo='RESTAURANTE')),
            drivers=Count('pk', filter=Q(tipo='ENTREGADOR')),
            customers=Count('pk', filter=Q(tipo='CLIENTE')))
        context['open_restaurants'] = Restaurante.objects.filter(aberto=True).count()
        shortcut('Gerenciar carteiras', 'wallet:management', 'cash-stack')
        shortcut('Todos os pedidos', 'orders:orders_list', 'bag-check')
        shortcut('Gerenciar usuários', 'core:usuario_list', 'people')
        shortcut('Monitorar entregadores', 'tracking:tracking-dashboard', 'geo-alt')
    elif profile and profile.tipo in ('RESTAURANTE', 'ENTREGADOR'):
        restaurant = getattr(profile, 'restaurante', None)
        driver = getattr(profile, 'entregador', None)
        if (profile.tipo == 'RESTAURANTE' and restaurant is None) or (profile.tipo == 'ENTREGADOR' and driver is None):
            context.update(heading='Cadastro incompleto', subtitle='Solicite ao administrador a conclusão do seu cadastro.')
            return context
        wallet = Wallet.objects.filter(usuario=profile).first()
        context['wallet'] = wallet
        metric('Saldo disponível', wallet.saldo if wallet else 0, 'Disponível na sua carteira', True)
        metric('Saldo reservado', wallet.saldo_reservado if wallet else 0, 'Fretes ou saques em processamento', True)
        context['transactions'] = WalletTransaction.objects.filter(wallet__usuario=profile).select_related('pedido')[:5]
        context['pending_count'] = FundingRequest.objects.filter(wallet__usuario=profile, status='pending').count()
        shortcut('Minha carteira e extrato', 'wallet:dashboard', 'wallet2')
        shortcut('Meus pedidos', 'orders:orders_list', 'bag-check')
        shortcut('Meu perfil', 'core:meu_perfil', 'person')
        if profile.tipo == 'RESTAURANTE':
            context.update(dashboard_role='restaurant', restaurant=restaurant,
                           heading=restaurant.nome_fantasia, subtitle='Acompanhe suas entregas e mantenha o saldo pronto para os próximos pedidos.')
            orders = orders.filter(restaurante=restaurant)
            metric('Pedidos de hoje', orders.filter(created_at__date=today).count(), 'Criados hoje pelo seu restaurante')
            metric('Aguardando entregador', orders.filter(status__in=['created', 'approved'], entregador__isnull=True).count(), 'Pedidos ainda sem entregador')
            shortcut('Criar pedido', 'orders:orders_criar', 'plus-circle')
            shortcut('Ver entregadores', 'tracking:tracking-dashboard', 'geo-alt')
            if not wallet or wallet.saldo <= 0:
                context['notices'].append('Sua carteira está sem saldo disponível. Solicite um depósito para reservar novos fretes.')
            if restaurant.latitude is None or restaurant.longitude is None:
                context['notices'].append('Complete a localização do restaurante no perfil para calcular o frete.')
        else:
            context.update(dashboard_role='driver', driver=driver, heading='Seu próximo destino começa aqui',
                           subtitle='Acompanhe suas corridas, seus ganhos e sua disponibilidade.')
            orders = orders.filter(entregador=driver)
            earnings = WalletTransaction.objects.filter(wallet__usuario=profile, tipo='DELIVERY_PAYMENT', created_at__date=today).aggregate(total=Sum('valor'))['total'] or Decimal('0')
            metric('Ganhos de hoje', earnings, 'Pagamentos de entrega creditados hoje', True)
            metric('Entregas concluídas hoje', orders.filter(status='delivered', updated_at__date=today).count(), 'Pedidos entregues hoje')
            context['available_orders'] = Order.objects.filter(entregador__isnull=True, status__in=['created', 'approved']).count()
            shortcut('Buscar corridas', 'orders:orders_dashboard', 'bicycle')
            if not driver.aprovado:
                context['notices'].append('Seu cadastro de entregador aguarda aprovação administrativa.')
            if not driver.ultima_localizacao:
                context['notices'].append('Ative o rastreamento para compartilhar sua localização durante as entregas.')
        metric('Em andamento', orders.filter(status__in=ACTIVE).count(), 'Pedidos ativos vinculados a você')
        metric('Entregues', orders.filter(status='delivered').count(), 'Total de entregas concluídas')
    else:
        context.update(heading='Bem-vindo ao Ask Delivery', subtitle='Acesse seus serviços pelo menu lateral.')
        return context

    context['active_orders'] = orders.filter(status__in=ACTIVE).order_by('-created_at')[:6]
    context['recent_orders'] = orders.filter(status__in=['delivered', 'canceled']).order_by('-updated_at')[:5]
    return context
