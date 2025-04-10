# home/urls.py
from django.urls import path
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),

    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    path('activity-logs/', views.activity_log_list, name='activity_log_list'),

    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('users/delete/<int:user_id>/', views.delete_user, name='delete_user'),

    path('manufacturers/', views.manufacturer_list, name='manufacturer_list'),
    path('manufacturers/add/', views.add_manufacturer, name='add_manufacturer'),
    path('manufacturers/edit/<int:manufacturer_id>/', views.edit_manufacturer, name='edit_manufacturer'),
    path('manufacturers/delete/<int:manufacturer_id>/', views.delete_manufacturer, name='delete_manufacturer'),

    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/edit/<int:category_id>/', views.edit_category, name='edit_category'),
    path('categories/delete/<int:category_id>/', views.delete_category, name='delete_category'),

    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('products/delete/<int:product_id>/', views.delete_product, name='delete_product'),

    path('inventory/', views.inventory_list, name='inventory_list'),

    path('purchase_transactions/', views.purchase_transaction_list, name='purchase_transaction_list'),
    path('purchase_transactions/add/', views.add_purchase_transaction, name='add_purchase_transaction'),
    path('purchase_transactions/delete/<int:transaction_id>/', views.delete_purchase_transaction, name='delete_purchase_transaction'),
    path("purchase_transaction/scan/", views.scan_purchase_transaction, name="scan_purchase_transaction"),
    
    path('get-products-by-manufacturer/', views.get_products_by_manufacturer, name='get_products_by_manufacturer'),
]