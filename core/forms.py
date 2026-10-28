# -*- coding: utf-8 -*-

from django import forms
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _

from .models import User, Usuario, Cliente, Restaurante, HorarioFuncionamento, Entregador, DocumentoEntregador


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'telefone',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sobrenome',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@exemplo.com',
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control phone-mask',
                'placeholder': 'Nome',
            }),
         }
        
class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite uma senha',
        })
    )

    confirm_password = forms.CharField(
        label='Confirmar senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme a senha',
        })
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # se existe instance com pk => UPDATE
        if self.instance and self.instance.pk:
            self.fields['password'].required = False
            self.fields['confirm_password'].required = False

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'telefone',
        ]


        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome',
            }),

            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sobrenome',
            }),

            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@exemplo.com',
            }),

            'telefone': forms.TextInput(attrs={
                'class': 'form-control phone-mask',
                'placeholder': '(00) 00000-0000',
            }),
    
        }

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')

        # só valida se alguma senha foi digitada
        if password or confirm:
            if password != confirm:
                raise forms.ValidationError(
                    'As senhas não coincidem.'
                )

        return cleaned_data
    def save(self, commit=True):
        user = super().save(commit=False)

        password = self.cleaned_data.get('password')

        if password:
            user.set_password(password)

        if commit:
            user.save()

        return user


class AdminUserUpdateForm(UserCreateForm):
    is_active = forms.BooleanField(
        required=False, label='Usuário ativo',
        help_text='Permite o acesso ao sistema. Ativar um cadastro pendente também aprova a solicitação.',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta(UserCreateForm.Meta):
        fields = [*UserCreateForm.Meta.fields, 'is_active']


class UsuarioForm(forms.ModelForm):

    class Meta:
        model = Usuario
        fields = [
            'foto',
        ]

        widgets = {
            'foto': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }


class ClienteForm(forms.ModelForm):
    data_nascimento = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'type': 'date',
                'class': 'form-control',
            }
        )
    )
    class Meta:
        model = Cliente
        fields = [
            'cpf',
            'data_nascimento',
            'aceita_marketing',
            'sexo',
            'address',
            'latitude',
            'longitude',
        ]


        widgets = {
            'cpf': forms.TextInput(attrs={
                'class': 'form-control cpf-mask',
                'placeholder': '000.000.000-00',
            }),

            'data_nascimento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),

            'aceita_marketing': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'sexo': forms.Select(attrs={
                'class': 'form-control',
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o endereço',
                'id': 'address-search',
                'autocomplete': 'off',
            }),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),

        }

class RestauranteForm(forms.ModelForm):

    class Meta:
        model = Restaurante
        fields = [
            'nome_fantasia',
            'razao_social',
            'cnpj',
            'descricao',
            'telefone_comercial',
            'taxa_entrega',
            'tempo_preparo_min',
            'aceita_retirada',
            'address',
            'latitude',
            'longitude',
        ]

        widgets = {
            'nome_fantasia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome Fantasia',
            }),

            'razao_social': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Razão Social',
            }),

            'cnpj': forms.TextInput(attrs={
                'class': 'form-control cnpj-mask',
                'placeholder': '00.000.000/0000-00',
            }),

            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição do restaurante',
            }),

            'telefone_comercial': forms.TextInput(attrs={
                'class': 'form-control phone-mask',
                'placeholder': '(00) 00000-0000',
            }),

            'taxa_entrega': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),

            'tempo_preparo_min': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
            }),

            'aceita_retirada': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o endereço',
                'id': 'address-search',
                'autocomplete': 'off',
            }),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),


        }

class HorarioFuncionamentoForm(forms.ModelForm):

    class Meta:
        model = HorarioFuncionamento
        fields = [
            'dia_semana',
            'hora_abertura',
            'hora_fechamento',
            'fechado',
        ]

        widgets = {
            'dia_semana': forms.Select(attrs={
                'class': 'form-select',
            }),

            'hora_abertura': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
            }),

            'hora_fechamento': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
            }),

            'fechado': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
        
class EntregadorForm(forms.ModelForm):
    data_nascimento = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'type': 'date',
                'class': 'form-control',
            }
        )
    )

    class Meta:
        model = Entregador
        fields = [
            'cpf',
            'cnh',
            'tipo_veiculo',
            'placa',  
            'data_nascimento',
            'sexo',
            'disponivel',
        ]

        widgets = {
            'cpf': forms.TextInput(attrs={
                'class': 'form-control cpf-mask',
                'placeholder': '000.000.000-00',
            }),

            'cnh': forms.TextInput(attrs={
                'class': 'form-control ',
                'placeholder': 'Número da CNH',
            }),

            'tipo_veiculo': forms.Select(attrs={
                'class': 'form-select',
            }),

            'placa': forms.TextInput(attrs={
                'class': 'form-control placa-mask',
                'placeholder': 'ABC-1234',
            }),

            'disponivel': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
             'data_nascimento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
             'sexo': forms.Select(attrs={
                'class': 'form-control',
            }),
             
        }
        
class DocumentoEntregadorForm(forms.ModelForm):

    class Meta:
        model = DocumentoEntregador
        fields = [
            'tipo',
            'arquivo',
            'aprovado',
        ]

        widgets = {
            'tipo': forms.Select(attrs={
                'class': 'form-select',
            }),

            'arquivo': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),

            'aprovado': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

class CadastroUserForm(UserCreateForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username=email).exists():
            raise forms.ValidationError('Já existe um cadastro com este email.')
        return email

    def clean(self):
        from django.contrib.auth.password_validation import validate_password
        data = super().clean()
        if data.get('password'):
            candidate = User(**{name: data.get(name, '') for name in ('first_name', 'last_name', 'email')})
            validate_password(data['password'], candidate)
        return data


def cadastro_forms(tipo, data=None, files=None):
    classes = {'CLIENTE': ClienteForm, 'RESTAURANTE': RestauranteForm, 'ENTREGADOR': EntregadorForm}
    user_form = CadastroUserForm(data, prefix='user')
    perfil_form = UsuarioForm(data, files, prefix='perfil')
    perfil_form.fields['foto'].required = True
    tipo_form = classes[tipo](data, prefix='dados')
    # Disponibilidade é operacional; não é uma escolha no cadastro público.
    tipo_form.fields.pop('disponivel', None)
    for name, field in tipo_form.fields.items():
        if not isinstance(field, forms.BooleanField):
            field.required = True
        if name in ('latitude', 'longitude'):
            field.widget = forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'})
            field.label = 'Latitude do endereço' if name == 'latitude' else 'Longitude do endereço'
            field.min_value = -90 if name == 'latitude' else -180
            field.max_value = 90 if name == 'latitude' else 180
            from django.core.validators import MinValueValidator, MaxValueValidator
            field.validators.extend([MinValueValidator(field.min_value), MaxValueValidator(field.max_value)])
    return user_form, perfil_form, tipo_form
