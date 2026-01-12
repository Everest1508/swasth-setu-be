from django.contrib import admin
from .models import Wallet, Transaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'wallet', 'transaction_type', 'amount', 'balance_after',
        'status', 'payment_method', 'created_at'
    )
    list_filter = ('transaction_type', 'status', 'payment_method', 'created_at')
    search_fields = (
        'wallet__user__username', 'wallet__user__email',
        'description', 'payment_gateway_transaction_id'
    )
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
