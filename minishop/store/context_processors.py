from .cart import Cart
from .models import Wishlist
from django.db.utils import OperationalError, ProgrammingError


def cart_items_count(request):
    cart = Cart(request)
    return {'cart_items_count': len(cart)}


def wishlist_count(request):
    """
    Return wishlist count but guard against missing DB tables (e.g., before migrations).
    This prevents site-wide 500/ProgrammingError during initial setup.
    """
    if not request.user.is_authenticated:
        return {'wishlist_count': 0}

    try:
        count = Wishlist.objects.filter(user=request.user).count()
    except (OperationalError, ProgrammingError):
        # The wishlist table may not exist yet (migrations not applied).
        # Return 0 as a safe fallback; advise running migrations.
        count = 0

    return {'wishlist_count': count}