from django import forms
from .models import Product, CATEGORIAS

PALAVRAS_PROIBIDAS = [
    'palavrao', 'ofensa', 'xingamento', 'idiota', 'imbecil',
    'merda', 'porra', 'caralho', 'puta', 'fdp', 'ilicito', 'drogas',
]


class ProductForm(forms.ModelForm):
    aceito_termos = forms.BooleanField(label='Eu aceito os termos (Leia nossos T&Cs)', required=True)

    class Meta:
        model = Product
        fields = ['titulo', 'categoria', 'preco', 'estoque', 'imagem', 'descricao', 'caracteristicas', 'frete_gratis']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Título do produto'}),
            'categoria': forms.Select(attrs={'class': 'form-input'}, choices=CATEGORIAS),
            'preco': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0,00', 'step': '0.01'}),
            'estoque': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Quantidade'}),
            'imagem': forms.FileInput(attrs={'class': 'form-input', 'accept': '.jpg,.jpeg,.png'}),
            'descricao': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Descrição do produto'}),
            'caracteristicas': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Uma característica por linha'}),
        }

    def clean_imagem(self):
        imagem = self.cleaned_data.get('imagem')
        if imagem:
            if imagem.size > 5 * 1024 * 1024:
                raise forms.ValidationError("A imagem deve ter no máximo 5 MB.")
            ext = imagem.name.lower().rsplit('.', 1)[-1] if '.' in imagem.name else ''
            if ext not in ('jpg', 'jpeg', 'png'):
                raise forms.ValidationError("Formato de imagem inválido. Use JPG ou PNG.")
        return imagem

    def clean_titulo(self):
        titulo = self.cleaned_data['titulo']
        for p in PALAVRAS_PROIBIDAS:
            if p in titulo.lower():
                raise forms.ValidationError("O título contém palavras não permitidas.")
        return titulo

    def clean_descricao(self):
        descricao = self.cleaned_data['descricao']
        for p in PALAVRAS_PROIBIDAS:
            if p in descricao.lower():
                raise forms.ValidationError("A descrição contém palavras não permitidas.")
        return descricao
