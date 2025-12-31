from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Wishlist
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from .models import Product, Order, OrderItem
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from .forms import CheckoutForm, ProductForm
from .cart import Cart

# Public Views
class HomeView(ListView):
    model = Product
    template_name = 'home.html'
    context_object_name = 'products'
    
    def get_queryset(self):
        return Product.objects.filter(status='ACTIVE', stock__gt=0)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.user.is_staff:
            # Calculate stats for admin users
            all_products = Product.objects.all()
            total_products = all_products.count()
            available_products = all_products.filter(status='ACTIVE', stock__gt=0).count()
            low_stock = all_products.filter(stock__gt=0, stock__lte=10).count()
            out_of_stock = all_products.filter(stock=0).count()
            
            context['stats'] = {
                'total_products': total_products,
                'available_products': available_products,
                'low_stock': low_stock,
                'out_of_stock': out_of_stock,
                'well_stocked': total_products - (low_stock + out_of_stock)
            }
        
        # Provide the current user's wishlist product ids so templates can mark items
        # as already wishlisted (for the heart icon / active state on product tiles).
        try:
            if self.request.user.is_authenticated:
                wishlist_ids = Wishlist.objects.filter(user=self.request.user).values_list('product_id', flat=True)
                context['user_wishlist_product_ids'] = set(wishlist_ids)
            else:
                context['user_wishlist_product_ids'] = set()
        except Exception:
            # If DB isn't ready (migrations), fail gracefully and show no wishlist items.
            context['user_wishlist_product_ids'] = set()

        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'product_detail.html'
    context_object_name = 'product'


def search_view(request):
    query = request.GET.get('q', '').strip()
    if query:
        products = Product.objects.filter(status='ACTIVE').filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    else:
        products = Product.objects.filter(status='ACTIVE', stock__gt=0)

    return render(request, 'home.html', {'products': products, 'query': query})


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Prefer cleaned_data email if form provides it, otherwise fall back to POST
            email = form.cleaned_data.get('email') if hasattr(form, 'cleaned_data') else None
            if not email:
                email = request.POST.get('email')
            if email:
                user.email = email
            user.save()
            auth_login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


@login_required
def profile_view(request):
    """Simple profile page for the current user."""
    return render(request, 'profile.html', {'user': request.user})

def cart_view(request):
    cart = Cart(request)
    return render(request, 'cart.html', {'cart': cart})

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, status='ACTIVE')
    cart = Cart(request)
    
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 1

        # Check existing quantity in cart for this product to avoid exceeding stock
        existing_qty = 0
        try:
            existing_qty = int(cart.cart.get(str(product.id), {}).get('quantity', 0))
        except Exception:
            existing_qty = 0

        if product.stock is None:
            available = 0
        else:
            available = product.stock - existing_qty

        if quantity <= 0:
            msg = 'Please select a valid quantity'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': msg}, status=400)
            messages.error(request, msg)
            next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
            return redirect(next_url or 'product_detail')

        if available <= 0 or quantity > available:
            if available <= 0:
                msg = f'Only 0 items left in stock for {product.name}'
            else:
                msg = f'Only {available} left in stock for {product.name}'

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': msg}, status=400)

            messages.error(request, msg)
            next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
            if next_url:
                return redirect(next_url)
            return redirect('product_detail', pk=product_id)

        # Safe to add
        cart.add(product, quantity)
        messages.success(request, f'Added {quantity} x {product.name} to cart')

        # If AJAX request, return JSON so frontend can update without reload
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': len(cart),
                'cart_total': str(cart.get_total())
            })

        # Respect `next` parameter from the form (so listing pages can stay on page)
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            return redirect(next_url)

    # Fallback: redirect to product detail if no next/referrer provided
    return redirect('product_detail', pk=product_id)

def update_cart(request, product_id):
    cart = Cart(request)

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 0))
        except (TypeError, ValueError):
            quantity = 0

        product = get_object_or_404(Product, id=product_id, status='ACTIVE')

        # Validate stock
        if quantity < 1:
            # treat as remove
            cart.remove(product_id)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'cart_count': len(cart), 'cart_total': str(cart.get_total())})
            messages.success(request, 'Item removed from cart')
            return redirect('cart')

        if product.stock is not None and quantity > product.stock:
            msg = f'Only {product.stock} left in stock for {product.name}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': msg}, status=400)
            messages.error(request, msg)
            return redirect('cart')

        # Update cart
        cart.update(product_id, quantity)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # compute item total
            item_total = None
            try:
                item_price = None
                item_data = cart.cart.get(str(product_id))
                if item_data:
                    item_price = item_data.get('price')
                    item_qty = item_data.get('quantity', 0)
                    from decimal import Decimal
                    item_total = str(Decimal(item_price) * int(item_qty))
            except Exception:
                item_total = None

            return JsonResponse({
                'success': True,
                'item_total': item_total,
                'cart_count': len(cart),
                'cart_total': str(cart.get_total())
            })

        messages.success(request, 'Cart updated')

    return redirect('cart')

def remove_from_cart(request, product_id):
    cart = Cart(request)
    if request.method == 'POST':
        cart.remove(product_id)
        # If AJAX, return JSON so frontend can update without reload
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': len(cart),
                'cart_total': str(cart.get_total())
            })
        messages.success(request, 'Item removed from cart')
    return redirect('cart')


def clear_cart(request):
    """Clear all items from the session cart."""
    cart = Cart(request)
    if request.method == 'POST':
        cart.clear()
        messages.success(request, 'Cart cleared')
    return redirect('cart')

def checkout_view(request):
    cart = Cart(request)
    
    if len(cart) == 0:
        messages.warning(request, 'Your cart is empty')
        return redirect('home')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create order
                    order = Order.objects.create(
                        customer_name=form.cleaned_data['name'],
                        customer_email=form.cleaned_data['email'],
                        customer_phone=form.cleaned_data['phone'],
                        shipping_address=form.cleaned_data['address'],
                        total_amount=cart.get_total()
                    )
                    
                    # Create order items and update stock
                    for item in cart:
                        product = item['product']
                        quantity = item['quantity']
                        
                        # Check stock
                        if product.stock < quantity:
                            raise ValueError(f'Insufficient stock for {product.name}')
                        
                        # Create order item
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            unit_price=product.price,
                            subtotal=quantity * product.price
                        )
                        
                        # Update stock
                        product.stock -= quantity
                        product.save()
                    
                    # Clear cart
                    cart.clear()
                    
                    return redirect('order_confirmation', order_id=order.id)
                    
            except ValueError as e:
                messages.error(request, str(e))
                return redirect('cart')
            except Exception as e:
                messages.error(request, 'An error occurred during checkout')
                return redirect('checkout')
    else:
        form = CheckoutForm()
    
    return render(request, 'checkout.html', {'form': form, 'cart': cart})

def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'order_confirmation.html', {'order': order})


@login_required
def orders_view(request):
    """List orders for the current user.

    Because `Order` isn't linked to `User` directly in the model,
    we match by the user's email when available. If no email/match,
    an empty list is returned.
    """
    user = request.user
    if user.is_authenticated and user.email:
        orders = Order.objects.filter(customer_email=user.email).order_by('-created_at')
    else:
        orders = Order.objects.none()

    return render(request, 'orders.html', {'orders': orders})

# Admin Views
@method_decorator(staff_member_required, name='dispatch')
class AdminProductListView(ListView):
    model = Product
    template_name = 'admin/product_list.html'
    context_object_name = 'products'

@method_decorator(staff_member_required, name='dispatch')
class AdminProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'admin/product_form.html'
    success_url = reverse_lazy('admin_product_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Product created successfully')
        return super().form_valid(form)

@method_decorator(staff_member_required, name='dispatch')
class AdminProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'admin/product_form.html'
    success_url = reverse_lazy('admin_product_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Product updated successfully')
        return super().form_valid(form)

@method_decorator(staff_member_required, name='dispatch')
class AdminProductDeleteView(DeleteView):
    model = Product
    template_name = 'admin/product_confirm_delete.html'
    success_url = reverse_lazy('admin_product_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Product deleted successfully')
        return super().delete(request, *args, **kwargs)
@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    wishlist_count = wishlist_items.count()
    
    return render(request, 'wishlist.html', {
        'wishlist_items': wishlist_items,
        'wishlist_count': wishlist_count,
        'cart_items_count': request.cart_count if hasattr(request, 'cart_count') else 0,
    })

def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Only accept POST for creating wishlist entries
    if request.method != 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
        messages.error(request, 'Invalid request method')
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    # Handle anonymous AJAX clients explicitly so they can be redirected on the frontend
    if not request.user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'login_required': True,
                'login_url': reverse('login')
            }, status=401)
        # non-AJAX -> use normal login redirect
        return redirect(f"{reverse('login')}?next={request.path}")

    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )

    wishlist_count = Wishlist.objects.filter(user=request.user).count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'created': created, 'wishlist_count': wishlist_count})

    # Non-AJAX fallback
    if created:
        messages.success(request, f'Added {product.name} to your wishlist')
    else:
        messages.info(request, f'{product.name} is already in your wishlist')

    return redirect(request.META.get('HTTP_REFERER', 'home'))

def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Only accept POST to modify data
    if request.method != 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
        return redirect(request.META.get('HTTP_REFERER', 'wishlist'))

    if not request.user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'login_required': True, 'login_url': reverse('login')}, status=401)
        return redirect(f"{reverse('login')}?next={request.path}")

    Wishlist.objects.filter(user=request.user, product=product).delete()

    wishlist_count = Wishlist.objects.filter(user=request.user).count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'wishlist_count': wishlist_count})

    return redirect(request.META.get('HTTP_REFERER', 'wishlist'))