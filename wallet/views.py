from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .forms import FundingRequestForm, DeliveryConfigForm
from .models import Wallet, FundingRequest, DeliveryConfig, WalletTransaction
from .services import WalletService


@login_required(login_url='/login/')
def dashboard(request):
    profile = getattr(request.user, 'perfil', None)
    if profile is None:
        messages.info(request, 'Complete seu perfil para acessar a carteira.')
        return redirect('core:meu_perfil')
    wallet, _ = Wallet.objects.get_or_create(usuario=profile)
    form = FundingRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            WalletService.solicitar(wallet, **form.cleaned_data)
        except ValueError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, 'Solicitação registrada. Aguarde a confirmação administrativa.')
            return redirect('wallet:dashboard')
    transactions = wallet.transacoes.select_related('pedido')
    kind = request.GET.get('tipo', '')
    if kind in WalletTransaction.Tipo.values:
        transactions = transactions.filter(tipo=kind)
    wallet.refresh_from_db()
    return render(request, 'wallet/dashboard.html', {
        'wallet': wallet, 'form': form, 'tipo': kind, 'types': WalletTransaction.Tipo.choices,
        'page_obj': Paginator(transactions, 20).get_page(request.GET.get('page')),
        'requests': wallet.solicitacoes.all()[:20],
    })


@user_passes_test(lambda user: user.is_superuser, login_url='/login/')
def management(request):
    config = DeliveryConfig.objects.order_by('pk').first()
    form = DeliveryConfigForm(request.POST or None, instance=config)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Tarifa atualizada. Pedidos já cotados mantêm seu valor.')
        return redirect('wallet:management')
    requests = FundingRequest.objects.select_related('wallet__usuario__user', 'reviewed_by')
    status = request.GET.get('status', 'pending')
    if status in FundingRequest.Status.values:
        requests = requests.filter(status=status)
    return render(request, 'wallet/management.html', {
        'form': form, 'page_obj': Paginator(requests, 20).get_page(request.GET.get('page')),
        'status': status, 'statuses': FundingRequest.Status.choices,
    })


@require_POST
@user_passes_test(lambda user: user.is_superuser, login_url='/login/')
def review(request, public_id):
    get_object_or_404(FundingRequest, public_id=public_id)
    if request.POST.get('decision') not in ('approve', 'reject'):
        messages.error(request, 'Selecione uma decisão válida.')
    else:
        try:
            WalletService.revisar(public_id, request.user, request.POST['decision'] == 'approve',
                                  request.POST.get('review_note', '')[:250])
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, 'Solicitação processada.')
    return redirect('wallet:management')


@login_required(login_url='/login/')
def quote(request):
    from django.http import JsonResponse
    from orders.models import Order
    from .services import DeliveryService
    if request.method != 'GET':
        return JsonResponse({'error': 'Método não permitido.'}, status=405)
    restaurant = getattr(getattr(request.user, 'perfil', None), 'restaurante', None)
    if restaurant is None:
        return JsonResponse({'error': 'Apenas restaurantes podem cotar entregas.'}, status=403)
    try:
        order = Order(restaurante=restaurant, latitude=request.GET.get('latitude'), longitude=request.GET.get('longitude'))
        distance, base, per_km, fee = DeliveryService.quote(order)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    wallet, _ = Wallet.objects.get_or_create(usuario=restaurant.usuario)
    return JsonResponse({'distance_km': str(distance), 'base': str(base), 'per_km': str(per_km),
                         'fee': str(fee), 'available': str(wallet.saldo), 'sufficient': wallet.saldo >= fee})
