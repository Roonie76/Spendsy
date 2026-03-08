from django.urls import path
from . import views

urlpatterns = [
    # 1. Health & Meta
    path('test/', views.health_check, name='health_check'),
    path('health/', views.health_check, name='health_check_v2'),
    path('ready/', views.readiness_check, name='readiness_check'),
    
    # 2. Auth 
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    
    # 3. Profile & Settings
    path('profile/<int:user_id>/', views.profile_settings, name='profile_settings'),
    
    # 4. Transactions
    path('add-transaction/', views.add_transaction, name='add_transaction'),
    path('history/<int:user_id>/', views.get_transaction_history, name='transaction-history'),
    path('summary/', views.financial_summary, name='financial_summary'),
    path('update-transaction/<int:pk>/', views.update_transaction, name='update_transaction'),
    path('delete-transaction/<int:pk>/', views.delete_transaction, name='delete_transaction'),
    
    # 5. Wealth Page
    path('get-wealth/<int:user_id>/', views.wealth_list_create, name='wealth-list-create'),
    path('delete-wealth/<int:item_id>/', views.delete_wealth_item, name='delete-wealth'),
    path('update-wealth/<int:item_id>/', views.update_wealth_item, name='update-wealth'),
    
    # 6. Tax & ITR
    path('tax-profile/<int:user_id>/', views.manage_tax_profile, name='manage_tax_profile'),
    
    # FIXED: Removed 'api/finance/' prefix because it's already handled in core/urls.py
    path('itr-data/<int:user_id>/', views.itr_data_handler, name='itr-handler'),
    path('parse-statement/', views.parse_statement_proxy, name='parse_statement_proxy'),
]
