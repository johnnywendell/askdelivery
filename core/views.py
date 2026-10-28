# -*- coding: utf-8 -*-

from django.contrib.auth.mixins import LoginRequiredMixin
from .dashboard import dashboard_context
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user_model, update_session_auth_hash,authenticate
from django.views.generic import View
from django.views.generic.edit import UpdateView
from django.utils.encoding import force_str
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth.models import Permission

from django.db.models.query_utils import Q
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.urls import reverse_lazy, reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template import loader

from django.db import transaction, DatabaseError
from .forms import UserForm, UserCreateForm, UsuarioForm, ClienteForm, RestauranteForm, EntregadorForm
from askdelivery.settings import DEFAULT_FROM_EMAIL

from django.views.generic import DeleteView
import operator
from functools import reduce
from .custom_views import CustomView, CustomDetailView,ListView, CustomTemplateView
from .models import Usuario, Cliente, Restaurante, Entregador, User
from .views_mixins import SuperUserRequiredMixin

DEFAULT_PERMISSION_MODELS = []

DEFAULT_PERMISSION_MODELS_STAFF = []
                               
CUSTOM_PERMISSIONS = []


class LoginView(View):
    template_name = 'accounts/login.html'
    success_url = reverse_lazy('core:index')
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.success_url)

        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(
            request,
            username=email,   # porque você salva username = email
            password=password
        )
        if user:
            login(request, user)
            return redirect(self.success_url)
        context = {
            'error': 'Email ou senha inválidos.'
        }
        return render(request, self.template_name, context)

class IndexView(LoginRequiredMixin, View):
    template_name = 'accounts/index.html'
    login_url = 'core:login'

    def get(self, request, *args, **kwargs):

        context = dashboard_context(request.user)
        return render(request, self.template_name, context)



class ClienteCreateView(SuperUserRequiredMixin,CustomView):
    template_name = 'accounts/cliente_form.html'
    success_url = reverse_lazy('core:usuario_list')

    def get(self, request, *args, **kwargs):

        context = {
            'user_form': UserCreateForm(),
            'usuario_form': UsuarioForm(),
            'cliente_form': ClienteForm(),
            'is_update': False,
        }

        return render(request, self.template_name, context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        user_form = UserCreateForm(request.POST)

        usuario_form = UsuarioForm(
            request.POST,
            request.FILES
        )

        cliente_form = ClienteForm(request.POST)


        



        if (
            user_form.is_valid()
            and usuario_form.is_valid()
            and cliente_form.is_valid()
        ):

            # salva User
            user = user_form.save(commit=False)
            user.set_password(
                user_form.cleaned_data['password']
            )
            user.username = user.email
            user.save()
            permission = Permission.objects.get(
                codename='cliente'
            )
            user.user_permissions.add(permission)

            # salva Usuario
            usuario = usuario_form.save(commit=False)


            usuario.user = user
            usuario.tipo = 'CLIENTE'

            if usuario_form.cleaned_data.get('foto'):
                usuario.foto = usuario_form.cleaned_data['foto']

            usuario.save()

            # salva Cliente
            cliente = cliente_form.save(commit=False)
            cliente.usuario = usuario
            cliente.save()

            return redirect(self.success_url)

        context = {
            'user_form': user_form,
            'usuario_form': usuario_form,
            'cliente_form': cliente_form,
            'is_update': False,
        }

        return render(request, self.template_name, context)

class ClienteUpdateView(SuperUserRequiredMixin,CustomView):

    template_name = 'accounts/cliente_form.html'
    success_url = reverse_lazy('core:usuario_list')

    def get_object(self):
        return Cliente.objects.select_related(
            'usuario__user'
        ).get(pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):

        cliente = self.get_object()

        context = {
            'user_form': UserCreateForm(
                instance=cliente.usuario.user
            ),
            'usuario_form': UsuarioForm(
                instance=cliente.usuario
            ),
            'cliente_form': ClienteForm(
                instance=cliente
            ),
            'object': cliente,
            'is_update': True,
        }

        return render(request, self.template_name, context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        cliente = self.get_object()

        user_form = UserCreateForm(
            request.POST,
            instance=cliente.usuario.user
        )

        usuario_form = UsuarioForm(
            request.POST,
            request.FILES,
            instance=cliente.usuario
        )

        cliente_form = ClienteForm(
            request.POST,
            instance=cliente
        )

        if (
            user_form.is_valid()
            and usuario_form.is_valid()
            and cliente_form.is_valid()
        ):

            # USER
            user = user_form.save(commit=False)
            user.username = user.email
            user.save()

            # USUARIO
            usuario = usuario_form.save(commit=False)
            usuario.user = user
            usuario.save()

            # CLIENTE
            cliente = cliente_form.save(commit=False)
            cliente.usuario = usuario
            cliente.save()

            return redirect(self.success_url)

        context = {
            'user_form': user_form,
            'usuario_form': usuario_form,
            'cliente_form': cliente_form,
            'object': cliente,
            'is_update': True,
        }

        return render(request, self.template_name, context)


class ClienteDetailView(SuperUserRequiredMixin,CustomDetailView):

    model = Cliente
    template_name = 'accounts/cliente_detail.html'

    def get_queryset(self):
        return Cliente.objects.select_related(
            'usuario__user'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class RestauranteCreateView(SuperUserRequiredMixin,CustomView):

    template_name = 'accounts/restaurante_form.html'
    success_url = reverse_lazy('core:usuario_list')

    def get(self, request, *args, **kwargs):

        context = {
            'user_form': UserCreateForm(),
            'usuario_form': UsuarioForm(),
            'restaurante_form': RestauranteForm(),
            'is_update': False,
        }

        return render(request, self.template_name, context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        user_form = UserCreateForm(request.POST)

        usuario_form = UsuarioForm(
            request.POST,
            request.FILES
        )

        restaurante_form = RestauranteForm(request.POST)
        
        



        if (
            user_form.is_valid()
            and usuario_form.is_valid()
            and restaurante_form.is_valid()
        ):

            # USER
            user = user_form.save(commit=False)
            user.set_password(
                user_form.cleaned_data['password']
            )
            user.username = user.email
            user.save()
            permission = Permission.objects.get(
                codename='restaurante'
            )
            user.user_permissions.add(permission)

            # USUARIO
            usuario = usuario_form.save(commit=False)
            usuario.user = user
            usuario.tipo = 'RESTAURANTE'

            if usuario_form.cleaned_data.get('foto'):
                usuario.foto = usuario_form.cleaned_data['foto']

            usuario.save()

            # RESTAURANTE
            restaurante = restaurante_form.save(commit=False)
            restaurante.usuario = usuario
            restaurante.save()
            
            return redirect(self.success_url)

        context = {
            'user_form': user_form,
            'usuario_form': usuario_form,
            'restaurante_form': restaurante_form,
            'is_update': False,
        }

        return render(request, self.template_name, context)

class RestauranteUpdateView(SuperUserRequiredMixin,CustomView):

    template_name = 'accounts/restaurante_form.html'
    success_url = reverse_lazy('core:usuario_list')

    def get_object(self):
        return Restaurante.objects.select_related(
            'usuario__user'
        ).get(pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):

        restaurante = self.get_object()

        context = {
            'user_form': UserCreateForm(
                instance=restaurante.usuario.user
            ),
            'usuario_form': UsuarioForm(
                instance=restaurante.usuario
            ),
            'restaurante_form': RestauranteForm(
                instance=restaurante
            ),
            'object': restaurante,
            'is_update': True,
        }

        return render(request, self.template_name, context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        restaurante = self.get_object()

        user_form = UserCreateForm(
            request.POST,
            instance=restaurante.usuario.user
        )

        usuario_form = UsuarioForm(
            request.POST,
            request.FILES,
            instance=restaurante.usuario
        )

        restaurante_form = RestauranteForm(
            request.POST,
            instance=restaurante
        )

        if (
            user_form.is_valid()
            and usuario_form.is_valid()
            and restaurante_form.is_valid()
        ):

            # USER
            user = user_form.save(commit=False)
            user.username = user.email
            user.save()

            # USUARIO
            usuario = usuario_form.save(commit=False)
            usuario.user = user
            usuario.save()

            # RESTAURANTE
            restaurante = restaurante_form.save(commit=False)
            restaurante.usuario = usuario
            restaurante.save()
            return redirect(self.success_url)

        context = {
            'user_form': user_form,
            'usuario_form': usuario_form,
            'restaurante_form': restaurante_form,
            'object': restaurante,
            'is_update': True,
        }

        return render(request, self.template_name, context)

class RestauranteDetailView(SuperUserRequiredMixin,CustomDetailView):

    model = Restaurante
    template_name = 'accounts/restaurante_detail.html'

    def get_queryset(self):
        return Restaurante.objects.select_related(
            'usuario__user'
        ).prefetch_related(
            'horarios'
        )

class EntregadorCreateView(SuperUserRequiredMixin,CustomView):

    template_name = 'accounts/entregador_form.html'
    success_url = reverse_lazy('core:usuario_list')

    def get(self, request, *args, **kwargs):

        context = {
            'user_form': UserCreateForm(),
            'usuario_form': UsuarioForm(),
            'entregador_form': EntregadorForm(),
            'is_update': False,
        }

        return render(request, self.template_name, context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        user_form = UserCreateForm(request.POST)

        usuario_form = UsuarioForm(
            request.POST,
            request.FILES
        )

        entregador_form = EntregadorForm(request.POST)

        if (
            user_form.is_valid()
            and usuario_form.is_valid()
            and entregador_form.is_valid()
        ):

            user = user_form.save(commit=False)
            user.set_password(
                user_form.cleaned_data['password']
            )
            user.username = user.email
            user.save()
            permission = Permission.objects.get(
                codename='entregador'
            )
            user.user_permissions.add(permission)

            usuario = usuario_form.save(commit=False)
            usuario.user = user
            usuario.tipo = 'ENTREGADOR'

            if usuario_form.cleaned_data.get('foto'):
                usuario.foto = usuario_form.cleaned_data['foto']

            usuario.save()

            entregador = entregador_form.save(commit=False)
            entregador.usuario = usuario
            entregador.save()

            return redirect(self.success_url)

        context = {
            'user_form': user_form,
            'usuario_form': usuario_form,
            'entregador_form': entregador_form,
            'is_update': False,
        }

        return render(request, self.template_name, context)    

class EntregadorUpdateView(SuperUserRequiredMixin, CustomView):

    template_name = 'accounts/entregador_form.html'
    success_url = reverse_lazy('core:usuario_list')

    def get_object(self):
        return Entregador.objects.select_related(
            'usuario__user'
        ).get(pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):

        entregador = self.get_object()

        context = {
            'user_form': UserCreateForm(
                instance=entregador.usuario.user
            ),
            'usuario_form': UsuarioForm(
                instance=entregador.usuario
            ),
            'entregador_form': EntregadorForm(
                instance=entregador
            ),
            'object': entregador,
            'is_update': True,
        }

        return render(request, self.template_name, context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        entregador = self.get_object()

        user_form = UserCreateForm(
            request.POST,
            instance=entregador.usuario.user
        )

        usuario_form = UsuarioForm(
            request.POST,
            request.FILES,
            instance=entregador.usuario
        )

        entregador_form = EntregadorForm(
            request.POST,
            instance=entregador
        )

        if (
            user_form.is_valid()
            and usuario_form.is_valid()
            and entregador_form.is_valid()
        ):
            user = user_form.save(commit=False)
            user.username = user.email
            user.save()

            usuario = usuario_form.save(commit=False)
            usuario.user = user
            usuario.save()

            entregador = entregador_form.save(commit=False)
            entregador.usuario = usuario
            entregador.save()

            return redirect(self.success_url)

        context = {
            'user_form': user_form,
            'usuario_form': usuario_form,
            'entregador_form': entregador_form,
            'object': entregador,
            'is_update': True,
        }

        return render(request, self.template_name, context)
    
class EntregadorDetailView(SuperUserRequiredMixin, CustomDetailView):

    model = Entregador
    template_name = 'accounts/entregador_detail.html'

    def get_queryset(self):
        return Entregador.objects.select_related(
            'usuario__user'
        ).prefetch_related(
            'documentos'
        )
        
        

class UsuarioListView(SuperUserRequiredMixin,CustomView, ListView):
    model = Usuario
    template_name = 'accounts/usuarios_list.html'
    context_object_name = 'usuarios'
    paginate_by = 10

    def get_queryset(self):
        queryset = Usuario.objects.select_related('user').all().order_by('-id')

        search = self.request.GET.get('search')

        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search)
            )

        return queryset

    def get_tipo_badge(self, tipo):
        badges = {
            'CLIENTE': 'primary',
            'RESTAURANTE': 'success',
            'ENTREGADOR': 'warning',
            'ADMIN': 'dark',
        }
        return badges.get(tipo, 'secondary')

    def get_urls(self, usuario):
        """
        Retorna urls corretas dependendo do tipo
        """

        if usuario.tipo == 'CLIENTE' and hasattr(usuario, 'cliente'):
            return {
                'detail': reverse('core:cliente_detail', kwargs={'pk': usuario.cliente.pk}),
                'update': reverse('core:cliente_update', kwargs={'pk': usuario.cliente.pk}),
            }

        elif usuario.tipo == 'RESTAURANTE' and hasattr(usuario, 'restaurante'):
            return {
                'detail': reverse('core:restaurante_detail', kwargs={'pk': usuario.restaurante.pk}),
                'update': reverse('core:restaurante_update', kwargs={'pk': usuario.restaurante.pk}),
            }

        elif usuario.tipo == 'ENTREGADOR' and hasattr(usuario, 'entregador'):
            return {
                'detail': reverse('core:entregador_detail', kwargs={'pk': usuario.entregador.pk}),
                'update': reverse('core:entregador_update', kwargs={'pk': usuario.entregador.pk}),
            }

        return {
            'detail': '#',
            'update': '#',
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        usuarios = context['usuarios']

        for usuario in usuarios:
            usuario.urls = self.get_urls(usuario)
            usuario.badge = self.get_tipo_badge(usuario.tipo)

        context['solicitacoes'] = Usuario.objects.filter(cadastro_pendente=True).select_related('user').order_by('criado_em')
        context['page_title'] = 'Usuários'
        context['search'] = self.request.GET.get('search', '')

        return context


class MeuPerfilView(CustomTemplateView):
    permission_codename = [
        'core.restaurante',
        'core.entregador',
        'core.cliente',
    ]
    template_name = 'accounts/meu_perfil.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        usuario = self.request.user.perfil

        context['user_form'] = UserForm(
            instance=self.request.user
        )

        context['usuario_form'] = UsuarioForm(
            instance=usuario
        )

        context['perfil'] = usuario

        context['tipo'] = usuario.tipo

        if usuario.tipo == 'CLIENTE':

            context['tipo_form'] = ClienteForm(
                instance=usuario.cliente
            )

        elif usuario.tipo == 'RESTAURANTE':

            context['tipo_form'] = RestauranteForm(
                instance=usuario.restaurante
            )

        elif usuario.tipo == 'ENTREGADOR':

            context['tipo_form'] = EntregadorForm(
                instance=usuario.entregador
            )

        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        usuario = request.user.perfil

        user_form = UserForm(
            request.POST,
            instance=request.user
        )

        usuario_form = UsuarioForm(
            request.POST,
            request.FILES,
            instance=usuario
        )

        tipo_form = None

        if usuario.tipo == 'CLIENTE':

            tipo_form = ClienteForm(
                request.POST,
                instance=usuario.cliente
            )

        elif usuario.tipo == 'RESTAURANTE':

            tipo_form = RestauranteForm(
                request.POST,
                instance=usuario.restaurante
            )

        elif usuario.tipo == 'ENTREGADOR':

            tipo_form = EntregadorForm(
                request.POST,
                instance=usuario.entregador
            )

        if (
            user_form.is_valid() and
            usuario_form.is_valid() and
            (tipo_form is None or tipo_form.is_valid())
        ):

            user_form.save()
            usuario_form.save()
            if tipo_form is not None:
                tipo_form.save()

            messages.success(
                request,
                'Perfil atualizado com sucesso.'
            )

            return redirect(
                'core:meu_perfil'
            )

        messages.error(
            request,
            'Erro ao atualizar perfil.'
        )

        return self.render_to_response({

            'user_form': user_form,
            'usuario_form': usuario_form,
            'tipo_form': tipo_form,
            'perfil': usuario,
            'tipo': usuario.tipo
        })

class UsuarioDeleteView(SuperUserRequiredMixin, DeleteView):
    model = User
    success_url = reverse_lazy('core:usuario_list')
    permission_codename = 'auth.delete_user'
    template_name = 'core/usuario_delete.html'
    def delete(self, request, *args, **kwargs):
        messages.success(
            request,
            'Usuário removido com sucesso.'
        )
        return super().delete(request, *args, **kwargs)





class SolicitarCadastroView(View):
    tipos = {'CLIENTE': 'Cliente', 'RESTAURANTE': 'Restaurante', 'ENTREGADOR': 'Entregador'}

    def get(self, request):
        return self.render(request)

    def render(self, request, forms=None):
        from .forms import cadastro_forms
        tipo = request.POST.get('tipo', '') if request.method == 'POST' else request.GET.get('tipo', '')
        if tipo not in self.tipos:
            tipo = 'CLIENTE'
        return render(request, 'accounts/solicitar_cadastro.html', {
            'tipo': tipo, 'tipos': self.tipos, 'forms': forms or cadastro_forms(tipo),
        })

    @transaction.atomic
    def post(self, request):
        from .forms import cadastro_forms
        from django.http import HttpResponseBadRequest
        tipo = request.POST.get('tipo')
        if tipo not in self.tipos:
            return HttpResponseBadRequest('Tipo de cadastro inválido.')
        forms = cadastro_forms(tipo, request.POST, request.FILES)
        if all([form.is_valid() for form in forms]):
            user_form, perfil_form, tipo_form = forms
            user = user_form.save(commit=False)
            user.username = user.email
            user.is_active = False
            user.save()
            perfil = perfil_form.save(commit=False)
            perfil.user = user
            perfil.tipo = tipo
            perfil.ativo = False
            perfil.cadastro_pendente = True
            perfil.save()
            dados = tipo_form.save(commit=False)
            dados.usuario = perfil
            dados.save()
            messages.success(request, 'Solicitação enviada. Aguarde a aprovação do administrador para entrar.')
            return redirect('core:login')
        return self.render(request, forms)


class AprovarCadastroView(SuperUserRequiredMixin, View):
    @transaction.atomic
    def post(self, request, pk):
        from django.shortcuts import get_object_or_404
        from django.utils import timezone
        perfil = get_object_or_404(Usuario.objects.select_for_update(), pk=pk)
        if perfil.cadastro_pendente:
            user = User.objects.select_for_update().get(pk=perfil.user_id)
            permission = Permission.objects.get(content_type__app_label='core', codename=perfil.tipo.lower())
            user.user_permissions.add(permission)
            user.is_active = True
            user.save(update_fields=['is_active'])
            perfil.ativo = True
            perfil.cadastro_pendente = False
            perfil.aprovado_em = timezone.now()
            perfil.aprovado_por = request.user
            perfil.save(update_fields=['ativo', 'cadastro_pendente', 'aprovado_em', 'aprovado_por'])
            if perfil.tipo == 'ENTREGADOR':
                Entregador.objects.filter(usuario=perfil).update(aprovado=True)
            messages.success(request, 'Cadastro aprovado. O usuário já pode entrar.')
        return redirect('core:usuario_list')
