from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
import os

# Conditionally import Cloudinary based on environment
if os.environ.get('VERCEL', '').lower() == 'true' or os.environ.get('USE_CLOUDINARY', '').lower() == 'true':
    from cloudinary.models import CloudinaryField
    USE_CLOUDINARY = True
else:
    from django.db.models import ImageField
    USE_CLOUDINARY = False


class Product(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=500, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(validators=[MinValueValidator(0)])
    
    # Dynamic field based on environment
    if USE_CLOUDINARY:
        image = CloudinaryField('image', folder='products/', blank=True, null=True)
    else:
        image = models.ImageField(upload_to='products/', blank=True, null=True)
    
    image_url = models.URLField(max_length=255, blank=True)  # legacy/optional
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    @property
    def is_available(self):
        return self.status == 'ACTIVE' and self.stock > 0

    @property
    def image_url_or_file(self):
        # For Cloudinary
        if USE_CLOUDINARY and self.image:
            try:
                # Get optimized URL with transformations
                return self.image.build_url(
                    width=600,
                    height=600,
                    crop="fill",
                    quality="auto",
                    fetch_format="auto"
                )
            except:
                return str(self.image)
        
        # For local/Pillow
        if not USE_CLOUDINARY and self.image:
            try:
                return self.image.url
            except ValueError:
                return ''
        
        # Fallback to image_url
        return self.image_url or ''

class Order(models.Model):
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    shipping_address = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='wishlisted_by')
    added_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'product']
        ordering = ['-added_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name}"