document.addEventListener('DOMContentLoaded', function() {
  const cartForms = Array.from(document.querySelectorAll('form[action*="add_to_cart"]'));
  cartForms.forEach(form => {
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.classList.add('btn-adding');
      }

      const cartIcon = document.querySelector('.bi-cart3') || document.querySelector('.bi-cart');
      if (cartIcon) {
        cartIcon.classList.add('cart-bump');
        setTimeout(() => cartIcon.classList.remove('cart-bump'), 700);
      }

      // small delay to show animation then submit for real
      setTimeout(() => form.submit(), 300);
    });
  });

  // Ensure quantity inputs respect min/max (additional safety)
  document.querySelectorAll('input[type="number"][name="quantity"]').forEach(input => {
    input.addEventListener('change', function() {
      const min = parseInt(this.getAttribute('min') || 1, 10);
      const max = parseInt(this.getAttribute('max') || 9999, 10);
      let v = parseInt(this.value || min, 10);
      if (isNaN(v) || v < min) v = min;
      if (v > max) v = max;
      this.value = v;
    });
  });
});
