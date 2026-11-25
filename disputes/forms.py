from django import forms


FORMATOS_EVIDENCIA = ('jpg', 'jpeg', 'png', 'mp4')
TAMANHO_MAX_EVIDENCIA = 10 * 1024 * 1024  # 10 MB

# Ao escolher um arquivo, o campo de nome vira obrigatório e recebe o foco (a validação real é no servidor)
_ONCHANGE_ARQUIVO = (
    "var n=this.form.elements['nome_evidencia'];"
    "if(n){n.required=this.files.length>0;if(this.files.length&&!n.value){n.focus();}}"
)


class EvidenciaFormMixin(forms.Form):
    """Campos de anexo usados em todos os formulários de disputa: arquivo + nome da evidência."""
    evidencia = forms.FileField(required=False, label='Evidência (JPG, PNG, MP4 até 10 MB)',
                                widget=forms.FileInput(attrs={'class': 'form-input', 'accept': '.jpg,.jpeg,.png,.mp4',
                                                              'onchange': _ONCHANGE_ARQUIVO}))
    nome_evidencia = forms.CharField(required=False, max_length=100, label='Nome da evidência',
                                     widget=forms.TextInput(attrs={'class': 'form-input', 'maxlength': '100',
                                                                   'placeholder': 'Ex.: Foto da caixa amassada'}))

    def clean_evidencia(self):
        f = self.cleaned_data.get('evidencia')
        if f:
            if f.size > TAMANHO_MAX_EVIDENCIA:
                raise forms.ValidationError("O arquivo deve ter no máximo 10 MB.")
            ext = f.name.lower().rsplit('.', 1)[-1] if '.' in f.name else ''
            if ext not in FORMATOS_EVIDENCIA:
                raise forms.ValidationError("Formato de arquivo inválido. Use JPG, PNG ou MP4.")
        return f

    def clean_nome_evidencia(self):
        return (self.cleaned_data.get('nome_evidencia') or '').strip()

    def clean(self):
        cleaned = super().clean()
        tem_arquivo = bool(cleaned.get('evidencia')) or 'evidencia' in self.errors
        nome = cleaned.get('nome_evidencia')
        if tem_arquivo and not nome:
            self.add_error('nome_evidencia', 'Dê um nome para a evidência e selecione o arquivo novamente.')
        elif nome and not tem_arquivo:
            self.add_error('evidencia', 'Você deu um nome à evidência, mas não escolheu o arquivo.')
        return cleaned


class DisputeForm(EvidenciaFormMixin):
    motivo = forms.CharField(max_length=200, label='Motivo da disputa',
                             widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex.: Produto não recebido'}))
    descricao = forms.CharField(label='Descreva o problema',
                                widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 4}))


class DisputeMessageForm(EvidenciaFormMixin):
    mensagem = forms.CharField(label='',
                               widget=forms.Textarea(attrs={
                                   'class': 'form-input',
                                   'rows': 2,
                                   'placeholder': 'Responder às partes...'
                               }))


class MediatorDecisionForm(forms.Form):
    fundamentacao = forms.CharField(label='Fundamentação',
                                    widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3}))
    decisao = forms.ChoiceField(label='Decisão', choices=[
        ('comprador', 'DECIDIR A FAVOR DO COMPRADOR'),
        ('vendedor', 'DECIDIR A FAVOR DO VENDEDOR'),
    ], widget=forms.RadioSelect())
