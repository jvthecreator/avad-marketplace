from django import forms


class DisputeForm(forms.Form):
    motivo = forms.CharField(max_length=200, label='Motivo da disputa',
                             widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex.: Produto não recebido'}))
    descricao = forms.CharField(label='Descreva o problema',
                                widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 4}))
    evidencia = forms.FileField(required=False, label='Evidência (JPG, PNG, MP4 até 10 MB)',
                                widget=forms.FileInput(attrs={'class': 'form-input', 'accept': '.jpg,.jpeg,.png,.mp4'}))

    def clean_evidencia(self):
        f = self.cleaned_data.get('evidencia')
        if f:
            if f.size > 10 * 1024 * 1024:
                raise forms.ValidationError("O arquivo deve ter no máximo 10 MB.")
            ext = f.name.lower().rsplit('.', 1)[-1] if '.' in f.name else ''
            if ext not in ('jpg', 'jpeg', 'png', 'mp4'):
                raise forms.ValidationError("Formato de arquivo inválido. Use JPG, PNG ou MP4.")
        return f


class DisputeMessageForm(forms.Form):
    mensagem = forms.CharField(label='',
                               widget=forms.Textarea(attrs={
                                   'class': 'form-input',
                                   'rows': 2,
                                   'placeholder': 'Responder às partes...'
                               }))
    evidencia = forms.FileField(required=False, label='Anexar evidência',
                                widget=forms.FileInput(attrs={'class': 'form-input', 'accept': '.jpg,.jpeg,.png,.mp4'}))


class MediatorDecisionForm(forms.Form):
    fundamentacao = forms.CharField(label='Fundamentação',
                                    widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3}))
    decisao = forms.ChoiceField(label='Decisão', choices=[
        ('comprador', 'DECIDIR A FAVOR DO COMPRADOR'),
        ('vendedor', 'DECIDIR A FAVOR DO VENDEDOR'),
    ], widget=forms.RadioSelect())
