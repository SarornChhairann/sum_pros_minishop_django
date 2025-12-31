from django.contrib import admin
from django import forms
from django.utils.safestring import mark_safe

from .models import Product

class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError('Price cannot be negative')
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is not None and stock < 0:
            raise forms.ValidationError('Stock cannot be negative')
        return stock

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('id', 'name', 'price', 'stock', 'status', 'is_available', 'created_at', 'image_preview')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('price', 'stock', 'status')
    readonly_fields = ('created_at', 'image_preview')
    fields = ('name', 'description', 'price', 'stock', 'status', 'image', 'image_url', 'image_preview', 'created_at')
    ordering = ('-created_at',)
    actions = ['mark_active', 'mark_inactive']

    def image_preview(self, obj):
        url = ''
        if obj.image:
            try:
                url = obj.image.url
            except ValueError:
                url = ''
        if not url and getattr(obj, 'image_url', ''):
            url = obj.image_url
        if url:
            return mark_safe(f'<img src="{url}" style="max-height:120px;" />')
        return 'No image'
    image_preview.short_description = 'Preview'

    def mark_active(self, request, queryset):
        updated = queryset.update(status='ACTIVE')
        self.message_user(request, f"Marked {updated} product(s) as active")
    mark_active.short_description = 'Mark selected products as Active'

    def mark_inactive(self, request, queryset):
        updated = queryset.update(status='INACTIVE')
        self.message_user(request, f"Marked {updated} product(s) as inactive")
    mark_inactive.short_description = 'Mark selected products as Inactive'