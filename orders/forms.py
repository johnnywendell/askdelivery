from django import forms
from .models import Order


class OrderForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and user.is_superuser:
            from core.models import Restaurante
            self.fields['restaurante'] = forms.ModelChoiceField(
                queryset=Restaurante.objects.filter(usuario__ativo=True, usuario__user__is_active=True),
                label='Restaurante responsável', widget=forms.Select(attrs={'class': 'form-select'}),
            )


    class Meta:
        model = Order
        fields = [
            'customer_name',
            'customer_phone',
            'latitude',
            'longitude',
            'cliente',
            'address',
        ]

        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do cliente',
            }),

            'customer_phone': forms.TextInput(attrs={
                'class': 'form-control phone-mask',
                'placeholder': 'Telefone',
            }),

            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o endereço',
                'id': 'address-search',
                'autocomplete': 'off',
            }),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),

            'cliente': forms.Select(attrs={
                'class': 'form-select',
            }),
            

        }

