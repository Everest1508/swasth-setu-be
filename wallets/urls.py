from django.urls import path
from .views import (
    get_wallet,
    get_transactions,
    add_balance,
    process_payment,
    pay_appointment,
    pay_order,
)

app_name = 'wallets'

urlpatterns = [
    path('', get_wallet, name='wallet'),
    path('transactions/', get_transactions, name='transactions'),
    path('add-balance/', add_balance, name='add-balance'),
    path('pay/', process_payment, name='process-payment'),
    path('pay-appointment/<int:appointment_id>/', pay_appointment, name='pay-appointment'),
    path('pay-order/<int:order_id>/', pay_order, name='pay-order'),
]




