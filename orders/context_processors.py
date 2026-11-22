from .cart import Cart


def cart_count(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {'cart_count': 0}
    return {'cart_count': Cart(request).count()}