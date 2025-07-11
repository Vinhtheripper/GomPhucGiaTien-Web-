from django.contrib import admin,messages
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from .utils import generate_invoice, send_invoice_email

from .models import (
    Product, Category, StockTransaction, ProductPriceConfig, ProductPriceHistory,
    Order, OrderItem, ShippingAddress, Customer, GuestOrder, Coupon, OrderSummary
)

# --- Resource Classes ---
class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'current_stock', 'created_at')

class ProductPriceConfigResource(resources.ModelResource):
    class Meta:
        model = ProductPriceConfig
        fields = (
            'id', 'product__name', 'base_cost_type', 'profit_margin',
            'vat_percent', 'discount_percent', 'active'
        )

class ProductPriceHistoryResource(resources.ModelResource):
    class Meta:
        model = ProductPriceHistory
        fields = ('id', 'product__name', 'old_price', 'new_price', 'changed_at', 'reason')

class OrderSummaryResource(resources.ModelResource):
    class Meta:
        model = OrderSummary
        fields = (
            'id', 'order__id', 'transaction_id', 'status', 'total_items',
            'total_amount', 'shipping_address', 'created_at', 'updated_at', 'note'
        )

# --- Admin Classes with ImportExport ---
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = ('name', 'price', 'current_stock', 'dynamic_price', 'is_new', 'display_category')
    search_fields = ('name',)
    list_filter = ('category',)
    readonly_fields = ('current_stock', 'dynamic_price', 'is_new')

    def dynamic_price(self, obj):
        return obj.get_dynamic_price()
    dynamic_price.short_description = 'Giá động'

    def display_category(self, obj):
        return ", ".join([cat.name for cat in obj.category.all()])
    display_category.short_description = "Danh mục"

    def current_stock(self, obj):
        return obj.current_stock
    current_stock.short_description = 'Tồn kho'

    def is_new(self, obj):
        return obj.is_new
    is_new.boolean = True
    is_new.short_description = "Mới"

class ProductPriceConfigAdmin(ImportExportModelAdmin):
    resource_class = ProductPriceConfigResource
    list_display = ('product', 'base_cost_type', 'profit_margin', 'vat_percent', 'discount_percent', 'active')
    list_filter = ('base_cost_type', 'active')
    search_fields = ('product__name',)

class ProductPriceHistoryAdmin(ImportExportModelAdmin):
    resource_class = ProductPriceHistoryResource
    list_display = ('product', 'old_price', 'new_price', 'changed_at', 'reason')
    list_filter = ('product',)
    search_fields = ('product__name',)

class OrderSummaryAdmin(ImportExportModelAdmin):
    resource_class = OrderSummaryResource
    list_display = ('order', 'transaction_id', 'status', 'total_items', 'total_amount', 'shipping_address', 'created_at', 'updated_at', 'note')
    list_filter = ('status',)
    search_fields = ('order__id',)

admin.site.register(OrderItem)
admin.site.register(ShippingAddress)
admin.site.register(Customer)
admin.site.register(GuestOrder)
admin.site.register(Coupon)
admin.site.register(Category)
admin.site.register(StockTransaction)

admin.site.register(Product, ProductAdmin)
admin.site.register(ProductPriceConfig, ProductPriceConfigAdmin)
admin.site.register(ProductPriceHistory, ProductPriceHistoryAdmin)
admin.site.register(OrderSummary, OrderSummaryAdmin)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'payment_method', 'complete', 'is_paid')
    list_filter = ('complete', 'is_paid')
    actions = ['mark_as_paid']

    def mark_as_paid(self, request, queryset):
        for order in queryset:
            if not order.is_paid:
                order.is_paid = True
                order.save()

                pdf_path = generate_invoice(order)


                if order.customer and order.customer.user and order.customer.user.email:
                    send_invoice_email(order.customer.user.email, pdf_path, order)
                    self.message_user(request, f" Invoice sent to {order.customer.user.email}", messages.SUCCESS)
                else:
                    self.message_user(request, "⚠ Customer email not found", messages.WARNING)
            else:
                self.message_user(request, f" Order {order.id} has been paid before", messages.ERROR)

    mark_as_paid.short_description = "Confirm payment & send invoice"
