# home/urls.py
from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import admin
from . import views
import os


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
    path('inventories/delete/<int:inventory_id>/', views.delete_inventory, name='delete_inventory'),

    path('purchase-transactions/', views.purchase_transaction_list, name='purchase_transaction_list'),
    path('purchase-transactions/add/', views.add_purchase_transaction, name='add_purchase_transaction'),
    path('purchase-transactions/delete/<int:transaction_id>/', views.delete_purchase_transaction, name='delete_purchase_transaction'),
    path("purchase-transactions/scan/", views.scan_purchase_transaction, name="scan_purchase_transaction"),
    
    path('get-products-by-manufacturer/', views.get_products_by_manufacturer, name='get_products_by_manufacturer'),

    path('customers/', views.customer_list, name='customer_list'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('customers/edit/<int:customer_id>/', views.edit_customer, name='edit_customer'),
    path('customers/delete/<int:customer_id>/', views.delete_customer, name='delete_customer'),

    path('sale-transactions/', views.sale_transaction_list, name='sale_transaction_list'),
    path('sale-transactions/add/', views.add_sale_transaction, name='add_sale_transaction'),
    path('sale-transactions/delete/<int:transaction_id>/', views.delete_sale_transaction, name='delete_sale_transaction'),
    path("sale-transactions/scan/", views.scan_sale_transaction, name="scan_sale_transaction"),

    path('get-inventory-price/<int:inventory_id>/', views.get_inventory_price, name='get_inventory_price'),

    path('reports/', views.report, name='report'),
    path('reports/pdf/', views.export_to_pdf, name='export_to_pdf'),

    path('api/get-object-details/<str:model_name>/<int:pk>/', views.get_object_details, name='get_object_details'),
    path("api/get-related-list/<str:related_model_name>/<str:parent_model_name>/<int:parent_id>/", views.get_related_list, name="get_related_list"),

    path('discounts/', views.discount_list, name='discount_list'),
    path('discounts/add/', views.add_discount, name='add_discount'),
    path('discounts/edit/<int:discount_id>/', views.edit_discount, name='edit_discount'),
    path('discounts/delete/<int:discount_id>/', views.delete_discount, name='delete_discount'),

    path("public-api/products/", views.public_product_list, name="public_product_list"),

    path('switch-language/', views.switch_language, name='switch_language'),
]

# Only include the admin panel if not in production
if os.getenv('DJANGO_ENV') != 'production':
    urlpatterns += [
        path('admin/', admin.site.urls),
    ]