from django import forms
from django.contrib.auth.models import User
from .models import UserProfile
import re
from datetime import date, datetime

PALAVRAS_PROIBIDAS = [
    'palavrao', 'ofensa', 'xingamento', 'idiota', 'imbecil',
    'merda', 'porra', 'caralho', 'puta', 'fdp', 'burro',
]


def check_palavras_proibidas(value, field_name):
    lower = value.lower()
    for p in PALAVRAS_PROIBIDAS:
        if p in lower:
            raise forms.ValidationError(f"O campo {field_name} contém palavras não permitidas.")


class RegisterForm(forms.Form):
    nome = forms.CharField(max_length=16, label='Nome',
                           widget=forms.TextInput(attrs={'placeholder': 'Apenas letras, máx. 16', 'class': 'form-input'}))
    data_nascimento = forms.CharField(max_length=10, label='Data de nascimento',
                                      widget=forms.TextInput(attrs={'placeholder': 'dd/mm/aaaa', 'class': 'form-input'}))
    email = forms.EmailField(max_length=64, label='Email',
                             widget=forms.EmailInput(attrs={'placeholder': 'seu@email.com', 'class': 'form-input'}))
    senha = forms.CharField(max_length=32, label='Senha',
                            widget=forms.PasswordInput(attrs={'placeholder': 'Mín. 8 caracteres', 'class': 'form-input'}))
    cpf = forms.CharField(max_length=14, label='CPF',
                          widget=forms.TextInput(attrs={'placeholder': '000.000.000-00', 'class': 'form-input'}))
    cnpj = forms.CharField(max_length=18, required=False, label='CNPJ (opcional)',
                           widget=forms.TextInput(attrs={'placeholder': '00.000.000/0000-00', 'class': 'form-input'}))

    def clean_nome(self):
        nome = self.cleaned_data['nome']
        if not re.match(r'^[a-zA-ZÀ-ÿ\s]+$', nome):
            raise forms.ValidationError("Nome deve conter apenas letras.")
        check_palavras_proibidas(nome, 'Nome')
        return nome

    def clean_data_nascimento(self):
        data_str = self.cleaned_data['data_nascimento']
        try:
            data = datetime.strptime(data_str, '%d/%m/%Y').date()
        except ValueError:
            raise forms.ValidationError("Data inválida. Use o formato dd/mm/aaaa.")
        hoje = date.today()
        idade = hoje.year - data.year - ((hoje.month, hoje.day) < (data.month, data.day))
        if idade <= 18:
            raise forms.ValidationError("Você deve ter mais de 18 anos para se cadastrar.")
        return data

    def clean_email(self):
        email = self.cleaned_data['email']
        check_palavras_proibidas(email, 'Email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email já está em uso")
        return email

    def clean_senha(self):
        senha = self.cleaned_data['senha']
        if len(senha) < 8:
            raise forms.ValidationError("A senha deve ter no mínimo 8 caracteres")
        check_palavras_proibidas(senha, 'Senha')
        return senha

    def clean_cpf(self):
        cpf = self.cleaned_data['cpf']
        if UserProfile.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError("CPF já está em uso")
        return cpf

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get('cnpj', '').strip()
        if cnpj and UserProfile.objects.filter(cnpj=cnpj).exists():
            raise forms.ValidationError("CNPJ já está em uso")
        return cnpj


class LoginForm(forms.Form):
    email = forms.EmailField(max_length=64, label='Email',
                             widget=forms.EmailInput(attrs={'placeholder': 'seu@email.com', 'class': 'form-input'}))
    senha = forms.CharField(max_length=32, label='Senha',
                            widget=forms.PasswordInput(attrs={'placeholder': 'Sua senha', 'class': 'form-input'}))
    tipo_usuario = forms.ChoiceField(label='Tipo de usuário', choices=[
        ('comprador', 'Comprador'),
        ('vendedor', 'Vendedor'),
        ('mediador', 'Mediador'),
    ], widget=forms.Select(attrs={'class': 'form-input'}))


class PasswordChangeForm(forms.Form):
    email = forms.EmailField(max_length=64, label='Email',
                             widget=forms.EmailInput(attrs={'placeholder': 'seu@email.com', 'class': 'form-input'}))
    nova_senha = forms.CharField(max_length=32, label='Nova senha',
                                 widget=forms.PasswordInput(attrs={'placeholder': 'Mín. 8 caracteres', 'class': 'form-input'}))

    def clean_nova_senha(self):
        senha = self.cleaned_data['nova_senha']
        if len(senha) < 8:
            raise forms.ValidationError("A senha deve ter no mínimo 8 caracteres")
        return senha
