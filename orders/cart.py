from django.db.models import Sum

from .models import CartItem


class Cart:
    """Carrinho do usuário logado, guardado no banco (tabela CartItem)."""

    def __init__(self, request):
        self.user = request.user

    def _qs(self):
        return CartItem.objects.filter(usuario=self.user)

    def get_qtd(self, product_id):
        item = self._qs().filter(produto_id=product_id).first()
        return item.quantidade if item else 0

    def set(self, product_id, qtd):
        if qtd < 1:
            self.remove(product_id)
            return
        CartItem.objects.update_or_create(
            usuario=self.user,
            produto_id=product_id,
            defaults={'quantidade': qtd},
        )

    def remove(self, product_id):
        self._qs().filter(produto_id=product_id).delete()

    def count(self):
        """Total de unidades no carrinho (usado no número do ícone)."""
        total = self._qs().filter(produto__ativo=True).aggregate(t=Sum('quantidade'))['t']
        return total or 0

    def items(self):
        result = []
        for row in self._qs().select_related('produto'):
            product = row.produto
            if not product.ativo:  # anúncio desativado: sai do carrinho
                row.delete()
                continue
            qtd = row.quantidade
            disponivel = product.estoque > 0
            if disponivel:
                qtd = min(qtd, product.estoque)
            result.append({
                'product': product,
                'qtd': qtd,
                'subtotal': product.preco * qtd,
                'disponivel': disponivel,
            })
        return result