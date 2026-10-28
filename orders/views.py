from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404,render, redirect
from django.contrib import messages
from core.models import Usuario
from .models import Order
from tracking.models import Entregador
from .serializers import OrderSerializer
from core.custom_views import CustomTemplateView, CreateView, ListView,CustomView, CustomDetailView
from .forms import OrderForm
from django.db import transaction
from django.urls import reverse_lazy,reverse
from django.db.models import Q
from wallet.services import DeliveryService
from rest_framework.exceptions import PermissionDenied, ValidationError

############# api views #############
class OrdersDashboardView(CustomTemplateView):
    template_name = "orders/dashboard.html"
    permission_codename = [
        'core.entregador',
    ]
class CreateOrderAPIView(APIView):

    def post(self, request):
        restaurant = getattr(getattr(request.user, 'perfil', None), 'restaurante', None)
        if request.user.is_superuser:
            from core.models import Restaurante
            from django import forms
            field = forms.ModelChoiceField(queryset=Restaurante.objects.filter(usuario__ativo=True, usuario__user__is_active=True))
            try:
                restaurant = field.clean(request.data.get('restaurante'))
            except forms.ValidationError as exc:
                raise ValidationError({'restaurante': exc.messages})
        if restaurant is None:
            raise PermissionDenied('Apenas restaurantes podem criar pedidos.')
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                order = serializer.save(restaurante=restaurant, status=Order.Status.APPROVED)
                order = DeliveryService.reserve(order)
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)})

        return Response({
            "success": True,
            "order_id": order.id
        }, status=status.HTTP_201_CREATED)
    
class OrderListAPIView(ListAPIView):

    serializer_class = OrderSerializer
    def get_queryset(self):
        entregador = getattr(getattr(self.request.user, 'perfil', None), 'entregador', None)
        if entregador is None:
            return Order.objects.none()

        return Order.objects.select_related(
            'entregador',
            'cliente',
            'restaurante'
        ).filter(
            Q(entregador__isnull=True, status__in=['approved', 'created']) |
            Q(entregador=entregador, status__in=['accepted', 'picking', 'in_transit'])
        ).order_by('-created_at')

class AcceptOrderAPIView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        order = get_object_or_404(Order.objects.select_for_update(), pk=pk)

        # verifica se já foi aceito
        if order.entregador is not None:
            return Response({
                'success': False,
                'message': 'Pedido já foi aceito'
            }, status=status.HTTP_400_BAD_REQUEST)

        # busca entregador logado
        usuario = get_object_or_404(
            Usuario,
            user=request.user
        )
        entregador = get_object_or_404(
            Entregador,
            usuario=usuario
        )
        # valida status
        if order.status not in ['approved', 'created']:
            return Response({
                'success': False,
                'message': 'Pedido não disponível'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = DeliveryService.reserve(order)
        except ValueError as exc:
            return Response({'success': False, 'message': str(exc)}, status=400)
        order.entregador = entregador
        order.status = Order.Status.ACCEPTED
        order.save()
        return Response({
            'success': True,
            'message': 'Pedido aceito com sucesso'
        }) 

############### views django ###############

class OrderListView(CustomView, ListView):
    model = Order
    template_name = 'orders/orders_list.html'
    context_object_name = 'orders'
    paginate_by = 10
    permission_codename = [
        'core.restaurante',
        'core.entregador',
        'core.cliente',
    ]
    def get_queryset(self):
        user = self.request.user
        
        queryset = Order.objects.select_related(
            'restaurante',
            'entregador',
            'cliente'
        ).all().order_by('-id')
        if user.is_superuser:
            return queryset
        if hasattr(user, 'perfil'):
            tipo = user.perfil.tipo
            # CLIENTE
            if tipo == 'CLIENTE':
                queryset = queryset.filter(
                    cliente=user.perfil.cliente
                )
            # RESTAURANTE
            elif tipo == 'RESTAURANTE':
                queryset = queryset.filter(
                    restaurante=user.perfil.restaurante
                )
            # ENTREGADOR
            elif tipo == 'ENTREGADOR':
                queryset = queryset.filter(
                    entregador=user.perfil.entregador
                )
        else:
            queryset = queryset.none()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(customer_name__icontains=search) |
                Q(restaurante__nome_fantasia__icontains=search)
            )
        return queryset

    # 🎯 badge de status
    def get_status_badge(self, status):

        badges = {
            'created': 'secondary',
            'approved': 'info',
            'accepted': 'primary',
            'picking': 'warning',
            'in_transit': 'dark',
            'delivered': 'success',
            'canceled': 'danger',
        }

        return badges.get(status, 'secondary')

    # 🔗 URLs futuras (detail/update)
    def get_urls(self, order):

        return {
            'detail': reverse('orders:order_detail', kwargs={'public_id': order.public_id}) if hasattr(order, 'pk') else '#',
            'update': reverse('orders:order_update', kwargs={'public_id': order.public_id}) if hasattr(order, 'pk') else '#',
        }

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        orders = context['orders']

        for order in orders:
            order.urls = self.get_urls(order)
            order.badge = self.get_status_badge(order.status)

        context['page_title'] = 'Pedidos'
        context['search'] = self.request.GET.get('search', '')

        return context
    
class OrderCreateView(CustomView):
    permission_codename = [
        'core.restaurante',
    ]
    template_name = 'orders/order_form.html'
    success_url = reverse_lazy('orders:orders_list')

    def get(self, request, *args, **kwargs):

        context = {
            'order_form': OrderForm(user=request.user),
            'is_update': False,
        }

        return render(request, self.template_name, context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        restaurant = getattr(getattr(request.user, 'perfil', None), 'restaurante', None)
        if restaurant is None and not request.user.is_superuser:
            from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
            raise DjangoPermissionDenied('Apenas restaurantes e administradores podem criar pedidos.')
        order_form = OrderForm(request.POST, user=request.user)

        if order_form.is_valid():

            order = order_form.save(commit=False)            
            order.status = Order.Status.APPROVED
            order.restaurante = order_form.cleaned_data['restaurante'] if request.user.is_superuser else restaurant
            try:
                with transaction.atomic():
                    order.save()
                    DeliveryService.reserve(order)
            except ValueError as exc:
                order_form.add_error(None, str(exc))
            else:
                return redirect(self.success_url)

        context = {
            'order_form': order_form,
            'is_update': False,
        }
        return render(request, self.template_name, context)

class OrderUpdateView(CustomView):
    permission_codename = [
        'core.restaurante',
    ]
    template_name = 'orders/order_form.html'
    success_url = reverse_lazy('orders:orders_list')
    slug_field = 'public_id'
    slug_url_kwarg = 'public_id'

    def get_object(self):
        return get_object_or_404(
            (Order.objects.select_for_update() if self.request.method == 'POST' else Order.objects.all()).select_related(
                'restaurante',
                'entregador',
                'cliente'
            ),
            public_id=self.kwargs['public_id'],
            restaurante__usuario__user=self.request.user,
            status__in=['created', 'approved'],
        )

    def get(self, request, *args, **kwargs):

        order = self.get_object()

        context = {
            'order_form': OrderForm(instance=order),
            'object': order,
            'is_update': True,
        }

        return render(request, self.template_name, context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        order = self.get_object()

        order_form = OrderForm(
            request.POST,
            instance=order
        )

        if order_form.is_valid():

            order = order_form.save(commit=False)

            # A cotação está reservada: alterações de destino exigem novo pedido.
            if any(field in order_form.changed_data for field in ['latitude', 'longitude', 'address']):
                order_form.add_error(None, 'Para alterar o destino, cancele este pedido e crie outro com um novo frete.')
            else:
                order.save()
                return redirect(self.success_url)

        return render(request, self.template_name, {
            'order_form': order_form,
            'object': order,
            'is_update': True,
        })
    
class OrderDetailView(CustomDetailView):
    permission_codename = [
        'core.restaurante',
        'core.entregador',
        'core.cliente',
    ]
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'object'
    slug_field = 'public_id'
    slug_url_kwarg = 'public_id'
    def get_queryset(self):
        profile = getattr(self.request.user, 'perfil', None)
        if self.request.user.is_superuser:
            return Order.objects.all()
        return Order.objects.filter(
            Q(restaurante__usuario=profile) | Q(entregador__usuario=profile) | Q(cliente__usuario=profile)
        ) if profile else Order.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = getattr(self.request.user, 'perfil', None)
        context['tipo_usuario'] = usuario.tipo if usuario else ''
        return context
    
    
class OrderTransitionView(CustomView):
    target_status = None

    def post(self, request, public_id):
        order = get_object_or_404(Order, public_id=public_id)
        try:
            order = DeliveryService.transition(order.pk, request.user, self.target_status)
        except PermissionError:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, 'Pedido atualizado com sucesso.')
        return redirect('orders:order_detail', public_id=order.public_id)


class OrderStartDeliveryView(OrderTransitionView):
    permission_codename = ['core.entregador']
    target_status = 'in_transit'


class OrderDeliveredView(OrderTransitionView):
    permission_codename = ['core.entregador']
    target_status = 'delivered'


class OrderCanceledView(OrderTransitionView):
    permission_codename = ['core.restaurante']
    target_status = 'canceled'
