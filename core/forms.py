from django import forms
from .models import Lancamento

class LancamentoForm(forms.ModelForm):
    class Meta:
        model = Lancamento
        fields = ['po', 'destino', 'quantidade', 'status', 'observacao']
        widgets = {
            'observacao': forms.Textarea(attrs={'rows': 3}),
            'destino': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_quantidade(self):
        quantidade = self.cleaned_data['quantidade']
        if quantidade <= 0:
            raise forms.ValidationError("Quantidade deve ser maior que zero")
        return quantidade