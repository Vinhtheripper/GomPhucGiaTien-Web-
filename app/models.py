from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta, datetime
from django import forms
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.db.models.signals import post_save
from django.dispatch import receiver


class CreateUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_active = False
        if commit:
            user.save()
        return user

class ChangePasswordForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current password'}),
        label="Current password"
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password'}),
        label="New password"
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repeat new password'}),
        label="Repeat new password"
    )


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200, null=True)
    customer_image = models.ImageField(upload_to='Profile/', null=True, blank=True)
    points = models.IntegerField(default=0)


    def __str__(self):
        return self.name if self.name else f"Customer {self.id}"

    def generate_reward_coupon(self):
        if self.redeem_reward():  # chỉ trừ điểm khi đủ
            coupon_code = 'RTX' + get_random_string(5).upper()
            coupon = Coupon.objects.create(
                code=coupon_code,
                coupon_type='reward',
                discount_percent=10,
                is_active=True,
                assigned_to=self,
            )
            return coupon
        return None

    @property
    def imageURL(self):
        try:
            url = self.customer_image.url
        except:
            url = ''
        return url



    def can_redeem_reward(self):
        return self.points >= 10

    def redeem_reward(self):

        if self.can_redeem_reward():
            self.points -= 10
            self.save()
            return True
        return False


class Category(models.Model):
    sub_category = models.ForeignKey('self', on_delete=models.CASCADE, related_name='sub_categories', null=True, blank=True)
    is_sub = models.BooleanField(default=False)
    name = models.CharField(max_length=200, null=True)
    slug = models.SlugField(max_length=200, unique=True)
    description= models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

def calculate_price(product):
    config = getattr(product, 'productpriceconfig', None)
    if not config or not config.active:
        return product.price  # fallback

    # Lấy base cost
    if config.base_cost_type == 'last_import':
        last_trans = StockTransaction.objects.filter(product=product, transaction_type='import').order_by('-date').first()
        base_cost = last_trans.price if last_trans else product.price
    elif config.base_cost_type == 'average_import':
        qs = StockTransaction.objects.filter(product=product, transaction_type='import')
        base_cost = qs.aggregate(avg=models.Avg('price'))['avg'] or product.price
    elif config.base_cost_type == 'manual':
        base_cost = product.price
    else:
        base_cost = product.price

    price = base_cost * (1 + config.profit_margin / 100)
    price = price * (1 + config.vat_percent / 100)
    price = price * (1 - config.discount_percent / 100)
    return round(price, 2)





class Product(models.Model):
    category = models.ManyToManyField(Category, related_name='product')
    name = models.CharField(max_length=200, null=True)
    price = models.FloatField()
    digital = models.BooleanField(default=False, null=True, blank=False)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    detail = models.TextField(null=True, blank=True)
    sale = models.BooleanField(default=False)
    discount_percentage = models.FloatField(default=0, null=True, blank=True)
    sale_price = models.FloatField(default=0, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def imageURL(self):
        try:
            url = self.image.url
        except:
            url = ''
        return url

    @property
    def is_new(self):
        now = timezone.now()
        return (now - self.created_at).days < 7

    @property
    def current_stock(self):
        from django.db.models import Sum
        return StockTransaction.objects.filter(product=self).aggregate(
            total=Sum('quantity')
        )['total'] or 0

    def get_dynamic_price(self):
        return calculate_price(self)



class Order(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('momo', 'Momo'),
        ('vnpay', 'VNPay'),
        ('bank', 'Bank Transfer'),
]
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True)
    date_order = models.DateTimeField(auto_now_add=True)
    cusnote = models.TextField(default="No note")
    complete = models.BooleanField(default=False, null=True, blank=False)
    transaction_id = models.CharField(max_length=200, null=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    is_scheduled = models.BooleanField(default=False)
    coupon = models.ForeignKey('Coupon', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Order {self.id} - {'Paid' if self.is_paid else 'Pending'}"

    @property
    def get_cart_items(self):
        order_items = self.orderitem_set.all()
        return sum([item.quantity for item in order_items])

    @property
    def get_cart_total(self):
        order_items = self.orderitem_set.all()
        return sum([Decimal(item.get_total) for item in order_items])

    @property
    def final_total(self):
        total = Decimal(str(self.get_cart_total))
        if self.coupon and self.coupon.is_valid():
            discount = total * Decimal(self.coupon.discount_percent) / 100
            total -= discount
        return total.quantize(Decimal("0.01"))

    @property
    def discount_amount(self):
        if self.coupon and self.coupon.is_valid():
            return (self.get_cart_total * Decimal(self.coupon.discount_percent)) / 100
        return Decimal('0.00')


class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.IntegerField(default=0, blank=0, null=True)
    date_added = models.DateTimeField(auto_now_add=True)

    @property
    def get_total(self):
        return self.product.price * self.quantity


class ShippingAddress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True)
    address = models.CharField(max_length=200, null=True)
    city = models.CharField(max_length=200, null=True)
    country = models.CharField(max_length=200, null=True)
    mobile = models.CharField(max_length=200, null=True)
    state = models.CharField(max_length=200, null=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.address if self.address else "No Address"



class GuestOrder(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='guest_order')
    name = models.CharField(max_length=200, null=True)
    email = models.EmailField(null=True)
    mobile = models.CharField(max_length=15, null=True)

    def __str__(self):
        return f"Guest Order for {self.name or 'Unknown'}"


class Coupon(models.Model):
    COUPON_TYPE = [
        ('reward', 'Reward Exchange'),  # RTXxxx
        ('general', 'General Use'),     # MACxxx
    ]

    code = models.CharField(max_length=10, unique=True)
    coupon_type = models.CharField(max_length=10, choices=COUPON_TYPE)
    discount_percent = models.PositiveIntegerField(default=0)  # Giảm giá theo %
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    assigned_to = models.ForeignKey(
        'Customer',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='coupons'
    )

    def is_valid(self):
        return self.is_active and (self.expires_at is None or timezone.now() <= self.expires_at)

    def __str__(self):
        return self.code

class OrderSummary(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='summary')
    transaction_id = models.CharField(max_length=200, null=True, blank=True)
    status_choices = [
        ('pending', 'Chờ xử lý'),
        ('processing', 'Đang xử lý'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã huỷ'),
        ('shipping', 'Đang giao hàng')
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='pending')
    total_items = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_address = models.CharField(max_length=300, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    note = models.TextField(null=True, blank=True)

    def update_from_order(self):
        self.transaction_id = self.order.transaction_id
        self.total_items = self.order.get_cart_items
        self.total_amount = self.order.final_total
        # Gộp thông tin địa chỉ từ ShippingAddress nếu có
        shipping = ShippingAddress.objects.filter(order=self.order).first()
        if shipping:
            self.shipping_address = f"{shipping.address}, {shipping.city}, {shipping.state}, {shipping.country}, {shipping.mobile}"
        self.save()

    def __str__(self):
        return f"OrderSummary for Order #{self.order.id}"


from django.conf import settings

class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('in', 'Nhập kho'),
        ('out', 'Xuất kho'),
        ('adjust', 'Điều chỉnh'),
        ('return_in', 'Nhập trả hàng'),
        ('return_out', 'Xuất trả khách'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()  # +: Nhập, -: Xuất
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)
    related_order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True
    )

    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.product.name} {self.quantity} ({self.date:%Y-%m-%d})"


class ProductPriceConfig(models.Model):
    BASE_COST_CHOICES = [
        ('last_import', 'Giá nhập gần nhất'),
        ('average_import', 'Giá nhập trung bình'),
        ('manual', 'Nhập tay (giữ nguyên giá product)'),
    ]
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    base_cost_type = models.CharField(max_length=20, choices=BASE_COST_CHOICES, default='last_import')
    profit_margin = models.FloatField(default=20)   # %
    vat_percent = models.FloatField(default=8)      # %
    discount_percent = models.FloatField(default=0) # %
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"Cấu hình giá {self.product.name}"


class ProductPriceHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    old_price = models.FloatField()
    new_price = models.FloatField()
    changed_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"Lịch sử giá {self.product.name} - {self.old_price} → {self.new_price}"



def update_product_price_and_history(product, reason="Tự động tính lại giá"):
    old_price = product.price
    new_price = calculate_price(product)
    if round(old_price, 2) != round(new_price, 2):
        product.price = new_price
        product.save(update_fields=['price'])
        ProductPriceHistory.objects.create(
            product=product,
            old_price=old_price,
            new_price=new_price,
            reason=reason
        )

@receiver(post_save, sender=StockTransaction)
def update_price_on_stock_change(sender, instance, **kwargs):
    # Chỉ cập nhật giá nếu là nhập kho và có config cho sản phẩm
    if ProductPriceConfig.objects.filter(product=instance.product, active=True).exists():
        update_product_price_and_history(instance.product, reason="Nhập/xuất kho")

@receiver(post_save, sender=ProductPriceConfig)
def update_price_on_config_change(sender, instance, **kwargs):
    update_product_price_and_history(instance.product, reason="Đổi cấu hình tính giá")


