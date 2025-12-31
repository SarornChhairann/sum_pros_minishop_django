from django.urls import path
from . import views

urlpatterns = [
    # Public URLs
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('', views.HomeView.as_view(), name='home'),
    path('products/', views.HomeView.as_view(), name='products'),
    path('search/', views.search_view, name='search'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('orders/', views.orders_view, name='orders'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('order/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    
    # Admin URLs
    path('admin/products/', views.AdminProductListView.as_view(), name='admin_product_list'),
    path('admin/products/new/', views.AdminProductCreateView.as_view(), name='admin_product_create'),
    path('admin/products/<int:pk>/edit/', views.AdminProductUpdateView.as_view(), name='admin_product_update'),
    path('admin/products/<int:pk>/delete/', views.AdminProductDeleteView.as_view(), name='admin_product_delete'),
]