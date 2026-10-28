from django.contrib import admin
from .models import Wallet, WalletTransaction, FundingRequest, DeliveryConfig


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Wallet)
class WalletAdmin(ReadOnlyAdmin):
    list_display = ['usuario', 'saldo', 'saldo_reservado']
    search_fields = ['usuario__user__email']


@admin.register(WalletTransaction)
class TransactionAdmin(ReadOnlyAdmin):
    list_display = ['wallet', 'tipo', 'valor', 'pedido', 'created_at']
    list_filter = ['tipo']


@admin.register(FundingRequest)
class RequestAdmin(ReadOnlyAdmin):
    list_display = ['public_id', 'wallet', 'kind', 'amount', 'status']
    list_filter = ['kind', 'status']


@admin.register(DeliveryConfig)
class ConfigAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return request.user.is_superuser and not DeliveryConfig.objects.exists()

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False
