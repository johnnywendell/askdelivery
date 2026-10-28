import uuid
from decimal import Decimal
from django import forms
from .models import FundingRequest, DeliveryConfig


class FundingRequestForm(forms.Form):
    public_id = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)
    kind = forms.ChoiceField(label='Operação', choices=FundingRequest.Kind.choices)
    amount = forms.DecimalField(label='Valor (R$)', min_value=Decimal('.01'), max_digits=10, decimal_places=2)
    note = forms.CharField(label='Observação / referência do comprovante', max_length=250, required=False,
                          help_text='Não informe senhas ou dados bancários completos.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not field.widget.is_hidden:
                field.widget.attrs['class'] = 'form-select' if isinstance(field, forms.ChoiceField) else 'form-control'


class DeliveryConfigForm(forms.ModelForm):
    class Meta:
        model = DeliveryConfig
        fields = ['valor_base', 'valor_km']
        labels = {'valor_base': 'Valor base (R$)', 'valor_km': 'Valor por km (R$)'}
        widgets = {key: forms.NumberInput(attrs={'class': 'form-control', 'step': '.01'})
                   for key in ['valor_base', 'valor_km']}
