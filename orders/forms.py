from django import forms


class CheckoutForm(forms.Form):
    cep = forms.CharField(max_length=10, label='CEP',
                          widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '00000-000'}))
    rua = forms.CharField(max_length=200, label='Rua',
                          widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Rua, número'}))
    complemento = forms.CharField(max_length=100, required=False, label='Complemento',
                                  widget=forms.TextInput(attrs={'class': 'form-input'}))
    bairro = forms.CharField(max_length=100, label='Bairro',
                             widget=forms.TextInput(attrs={'class': 'form-input'}))
    cidade = forms.CharField(max_length=100, label='Cidade',
                             widget=forms.TextInput(attrs={'class': 'form-input'}))
    estado = forms.CharField(max_length=2, label='Estado',
                             widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'UF'}))

    metodo_frete = forms.ChoiceField(label='Método de envio', choices=[
        ('pac', 'PAC'),
        ('sedex', 'SEDEX'),
    ], widget=forms.RadioSelect())

    forma_pagamento = forms.ChoiceField(label='Forma de pagamento', choices=[
        ('cartao', 'Cartão de crédito'),
        ('pix', 'PIX'),
        ('boleto', 'Boleto'),
    ], widget=forms.RadioSelect())

    numero_cartao = forms.CharField(max_length=19, required=False, label='Número do cartão',
                                    widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '0000 0000 0000 0000'}))
    nome_cartao = forms.CharField(max_length=64, required=False, label='Nome impresso',
                                  widget=forms.TextInput(attrs={'class': 'form-input'}))
    validade_cartao = forms.CharField(max_length=5, required=False, label='Validade',
                                     widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'MM/AA'}))
    cvv = forms.CharField(max_length=4, required=False, label='CVV',
                          widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '000'}))
    cpf_titular = forms.CharField(max_length=14, required=False, label='CPF do titular',
                                  widget=forms.TextInput(attrs={'class': 'form-input'}))
    parcelas = forms.ChoiceField(required=False, label='Parcelamento', choices=[
        (1, '1x sem juros'),
        (2, '2x sem juros'),
        (3, '3x sem juros'),
        (6, '6x sem juros'),
        (12, '12x sem juros'),
    ], widget=forms.Select(attrs={'class': 'form-input'}))
    salvar_cartao = forms.BooleanField(required=False, label='Salvar cartão para próximas compras')
    endereco_cobranca_igual = forms.BooleanField(required=False, label='Endereço de cobrança igual ao de entrega',
                                                  initial=True)

    simulacao_gateway = forms.ChoiceField(label='Simulação de gateway', choices=[
        ('aprovar', 'Aprovar Pagamento'),
        ('negar', 'Simular Transação Negada'),
        ('timeout', 'Simular Timeout > 40s'),
    ], widget=forms.Select(attrs={'class': 'form-input'}), initial='aprovar')

    quantidade = forms.IntegerField(min_value=1, initial=1, widget=forms.HiddenInput())
    cartao_salvo = forms.IntegerField(required=False, widget=forms.HiddenInput())


class RefundForm(forms.Form):
    motivo = forms.ChoiceField(label='Motivo do reembolso', choices=[
        ('insatisfeito', 'Não estou satisfeito com o produto'),
        ('defeito', 'Produto com defeito'),
        ('diferente', 'Produto diferente do anunciado'),
        ('danificado', 'Produto danificado no transporte'),
        ('atraso', 'Atraso excessivo na entrega'),
        ('outro', 'Outro motivo'),
    ], widget=forms.Select(attrs={'class': 'form-input'}))
    comentario = forms.CharField(required=False, label='Comentário (opcional)',
                                 widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3}))


class ReviewForm(forms.Form):
    nota_vendedor = forms.IntegerField(min_value=0, max_value=5, initial=0,
                                       widget=forms.HiddenInput(attrs={'id': 'nota_vendedor'}))
    comentario_vendedor = forms.CharField(required=False, label='Comentário (opcional)',
                                          widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3}))
    nota_transporte = forms.IntegerField(min_value=0, max_value=5, initial=0,
                                         widget=forms.HiddenInput(attrs={'id': 'nota_transporte'}))
    comentario_transporte = forms.CharField(required=False, label='Comentário (opcional)',
                                            widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3}))

    def clean(self):
        cleaned = super().clean()
        campos = {
            'nota_vendedor': 'Vendedor',
            'nota_transporte': 'Empresa de Transporte',
        }
        # nota 0 (ou ausente) não é permitida: é preciso dar pelo menos 1 estrela
        faltando = [nome for campo, nome in campos.items() if not cleaned.get(campo)]
        for campo in campos:
            if not cleaned.get(campo) and campo not in self.errors:
                self.add_error(campo, 'Selecione pelo menos 1 estrela.')
        if faltando:
            raise forms.ValidationError(
                'Para enviar a avaliação, dê pelo menos 1 estrela para: ' + ' e '.join(faltando) + '.'
            )
        return cleaned