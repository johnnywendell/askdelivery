
from django.urls import path
from . import views as v
from django.contrib.auth.views import LogoutView

app_name = 'core'
urlpatterns = [
    path('', v.IndexView.as_view(), name='index'),
    path('cadastro/', v.SolicitarCadastroView.as_view(), name='solicitar_cadastro'),
    path('usuarios/<int:pk>/aprovar/', v.AprovarCadastroView.as_view(), name='aprovar_cadastro'),
    path('login/', v.LoginView.as_view(), name='login'),
    path('logout/',
            LogoutView.as_view(next_page='core:login'),
            name='logout'
        ),
    path(r'criarcliente/',
        v.ClienteCreateView.as_view(), name='criarcliente'),
    path(r'editarcliente/<int:pk>/',
        v.ClienteUpdateView.as_view(), name='cliente_update'),
    path(r'detailcliente/<int:pk>/',
        v.ClienteDetailView.as_view(), name='cliente_detail'),
    
    path(r'criarrestaurante/',
        v.RestauranteCreateView.as_view(), name='criarrestaurante'),
    path(r'editarrestaurante/<int:pk>/',
        v.RestauranteUpdateView.as_view(), name='restaurante_update'),
    path(r'detailrestaurante/<int:pk>/',
        v.RestauranteDetailView.as_view(), name='restaurante_detail'),
    
    path(r'criarentregador/',
        v.EntregadorCreateView.as_view(), name='criarentregador'),
    path(r'editarentregador/<int:pk>/',
        v.EntregadorUpdateView.as_view(), name='entregador_update'),
    path(r'detailentregador/<int:pk>/',
        v.EntregadorDetailView.as_view(), name='entregador_detail'),
    
    path('usuarios/', v.UsuarioListView.as_view(), name='usuario_list'),
    path('meu-perfil/',v.MeuPerfilView.as_view(),name='meu_perfil'),

    path('usuarios/delete/<int:pk>/',v.UsuarioDeleteView.as_view(),name='usuario_delete'),

]

