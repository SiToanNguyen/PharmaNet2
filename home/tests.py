# home/tests.py
from threading import Thread
from datetime import date

from django.test import TransactionTestCase, TestCase, Client
"""
Django's regular TestCase wraps every test method inside a single atomic transaction and rolls it back after the test. 
This makes tests fast but prevents us from observing real commit-related behavior. So, if we want to test:
    - What happens after a transaction is committed
    - Whether two threads conflict over the same database row
    - How locking (e.g., select_for_update) works
We need TransactionTestCase.
"""
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages

from home.models import (
    Product, Inventory, Category, Manufacturer,
    Customer, SaleTransaction, SoldProduct,
    ActivityLog
)

class BlackBoxTests(TestCase):
    """
    Black-box test:
        - Given a known input.
        - Do not care how the system processes it internally.
        - Search in the database. If the exact match cannot be found, the test fails.
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='tester', password='pass', is_staff=True)
        self.client.login(username='tester', password='pass')

    def test_add_manufacturer_exact_match(self):
        test_input = {
            'name': 'Moore Group',
            'address': 'Burnettland 03909',
            'phone_number': '001-412-604-9045',
            'email': 'davisbonnie@johnson-hudson.com'
        }

        self.client.post(reverse('add_manufacturer'), data=test_input)

        exists = Manufacturer.objects.filter(**test_input).exists()
        self.assertTrue(
            exists,
            f"❌ Manufacturer not found in DB with input: {test_input}"
        )
        print("✅ test_add_manufacturer_exact_match passed")

class ConcurrentSaleTests(TransactionTestCase):
    """
    Test scenario:
        - There is only 1 unit of a product in Inventory.
        - Multiple users attempt to purchase this product concurrently.
        - Only one sale should succeed, the rest should fail due to insufficient quantity.
    """
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Test Category", low_stock_threshold=1)
        self.manufacturer = Manufacturer.objects.create(name="Test Manufacturer")
        self.product = Product.objects.create(
            name="Limited Product",
            category=self.category,
            manufacturer=self.manufacturer,
            sale_price=10.00,
            description="Only 1 in stock"
        )
        self.inventory = Inventory.objects.create(
            product=self.product,
            quantity=1,
            expiry_date=date.today()
        )
        self.customer = Customer.objects.create(
            full_name="Test Customer",
            birthdate="1990-01-01",
            phone_number="1234567890",
            email="test@example.com",
            address="123 Test St"
        )

    def simulate_sale(self, transaction_number, results, index):
        user = User.objects.create_user(username=f'user{index}', password='pass', is_staff=True)
        c = Client()
        c.login(username=f'user{index}', password='pass')

        response = c.post('/sale_transactions/add/', {
            'transaction_number': transaction_number,
            'transaction_date': '2025-06-17',
            'customer': self.customer.id,
            'discount': 0,
            'cash_received': 10,
            'payment_method': 'Cash',
            'remarks': '',
            'products-TOTAL_FORMS': '1',
            'products-INITIAL_FORMS': '0',
            'products-0-inventory_item': self.inventory.id,
            'products-0-quantity': '1',
        }, follow=True)
        if response.status_code == 200 and SaleTransaction.objects.filter(transaction_number=transaction_number).exists():
            results[index] = f"✅ Success: Thread {index}, TXN {transaction_number}"
        else:
            results[index] = f"❌ Failed: Thread {index}, TXN {transaction_number}"

        print(f"[Thread {index}] Response Code: {response.status_code}")

        if hasattr(response, 'context') and response.context:
            form = response.context.get('form')
            if form:
                print("Form errors:", form.errors)
            formset = response.context.get('formset')
            if formset:
                print("Formset errors:", formset.errors)
        else:
            print("No response context (likely a redirect or raw response)")

    def test_concurrent_sales_for_limited_inventory(self):
        thread_count = 10
        threads = []
        results = [None] * thread_count

        for i in range(thread_count):
            txn_number = f'TXN-{i}'
            t = Thread(target=self.simulate_sale, args=(txn_number, results, i))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        success_count = SaleTransaction.objects.count()
        sold_count = SoldProduct.objects.count()
        final_quantity = Inventory.objects.get(pk=self.inventory.pk).quantity

        for result in results:
            print(result)

        print(f"✅ Sale Transactions created: {success_count}")
        print(f"✅ Sold Products created: {sold_count}")
        print(f"✅ Final Inventory Quantity: {final_quantity}")

        self.assertEqual(success_count, 1)
        self.assertEqual(sold_count, 1)
        self.assertEqual(final_quantity, 0)

class FunctionalViewTests(TestCase):
    """    
    Test the Django views in views.py. Simulate how a real user uses forms on website to perform these actions:
        - Add, Edit, Delete User
        - Add, Edit, Delete Category
        - Add, Edit, Delete Manufacturer
        - Add, Edit, Delete Product
        - Add, Edit, Delete Customer
    Test succeeds if:
        - Data is saved in database.
        - Activity log is created.
        - Message is correct.
        - Redirect to the correct page.
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='pass', is_staff=True, is_superuser=True)
        self.client.login(username='admin', password='pass')

    # Helper function to assert that an activity log entry exists
    def assertActivityLog(self, user, action, obj_id):
        self.assertTrue(ActivityLog.objects.filter(
            user=user,
            action__icontains=action,
            additional_info__icontains=str(obj_id)
        ).exists(), f"Missing log for: {action} / ID: {obj_id}")

    # Helper function to check if a message is present in the response
    def assertMessagePresent(self, response, expected_text):
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(expected_text in str(m) for m in messages),
            f"Expected message '{expected_text}' not found in: {[str(m) for m in messages]}"
        )

    def test_add_edit_delete_user(self):
        data = {
            'username': 'newuser',
            'password': 'newpass123',
            'email': 'user@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'is_staff': 'on',
            'is_superuser': 'on',
            'is_active': 'on',
        }        
        username = data['username']
        response = self.client.post(reverse('add_user'), data, follow=True)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        user_obj = User.objects.get(username='newuser') # check if user was created
        self.assertActivityLog(self.user, "added new user", user_obj.id) # check if activity log was created
        self.assertMessagePresent(response, f"The user '{username}' added.") # check if message is correct
        self.assertRedirects(response, reverse('user_list')) # check if redirected to user list
        print("✅ Add User passed")

        user_id = User.objects.get(username='newuser').id
        data['first_name'] = 'Updated'
        response = self.client.post(reverse('edit_user', args=[user_id]), data, follow=True)
        self.assertEqual(User.objects.get(id=user_id).first_name, 'Updated')
        self.assertActivityLog(self.user, "edited user", user_obj.id)
        self.assertMessagePresent(response, f"The user '{username}' updated.")
        self.assertRedirects(response, reverse('user_list'))
        print("✅ Edit User passed")

        response = self.client.post(reverse('delete_user', args=[user_id]), follow=True)
        self.assertFalse(User.objects.filter(id=user_id).exists())
        self.assertActivityLog(self.user, "deleted user", user_obj.id)
        self.assertMessagePresent(response, f"The user '{username}' deleted.")
        self.assertRedirects(response, reverse('user_list'))
        print("✅ Delete User passed")

    def test_add_edit_delete_category(self):
        data = {
            'name': 'Analgesics',
            'description': 'Pain relievers',
            'requires_prescription': 'on',
            'low_stock_threshold': 5
        }
        name = data['name']
        response = self.client.post(reverse('add_category'), data, follow=True)
        obj = Category.objects.get(name='Analgesics')
        self.assertActivityLog(self.user, "added new category", obj.id)
        self.assertMessagePresent(response, f"The category '{name}' added.")
        self.assertRedirects(response, reverse('category_list'))
        print("✅ Add Category passed")

        data['description'] = 'Updated description'
        response = self.client.post(reverse('edit_category', args=[obj.id]), data, follow=True)
        self.assertEqual(Category.objects.get(id=obj.id).description, 'Updated description')
        self.assertActivityLog(self.user, "edited category", obj.id)
        self.assertMessagePresent(response, f"The category '{name}' updated.")
        self.assertRedirects(response, reverse('category_list'))
        print("✅ Edit Category passed")

        response = self.client.post(reverse('delete_category', args=[obj.id]), follow=True)
        self.assertFalse(Category.objects.filter(id=obj.id).exists())
        self.assertActivityLog(self.user, "deleted category", obj.id)
        self.assertMessagePresent(response, f"The category '{name}' deleted.")
        self.assertRedirects(response, reverse('category_list'))
        print("✅ Delete Category passed")

    def test_add_edit_delete_manufacturer(self):
        data = {
            'name': 'Acme Corp',
            'address': '123 Pharma Street',
            'phone_number': '+1-800-555-0000',
            'email': 'acme@example.com'
        }
        name = data['name']
        response = self.client.post(reverse('add_manufacturer'), data, follow=True)
        obj = Manufacturer.objects.get(name='Acme Corp')
        self.assertActivityLog(self.user, "added new manufacturer", obj.id)
        self.assertMessagePresent(response, f"The manufacturer '{name}' added.")
        self.assertRedirects(response, reverse('manufacturer_list'))
        print("✅ Add Manufacturer passed")

        data['address'] = 'Updated Address'
        response = self.client.post(reverse('edit_manufacturer', args=[obj.id]), data, follow=True)
        self.assertEqual(Manufacturer.objects.get(id=obj.id).address, 'Updated Address')
        self.assertActivityLog(self.user, "edited manufacturer", obj.id)
        self.assertMessagePresent(response, f"The manufacturer '{name}' updated.")
        self.assertRedirects(response, reverse('manufacturer_list'))
        print("✅ Edit Manufacturer passed")

        response = self.client.post(reverse('delete_manufacturer', args=[obj.id]), follow=True)
        self.assertFalse(Manufacturer.objects.filter(id=obj.id).exists())
        self.assertActivityLog(self.user, "deleted manufacturer", obj.id)
        self.assertMessagePresent(response, f"The manufacturer '{name}' deleted.")
        self.assertRedirects(response, reverse('manufacturer_list'))
        print("✅ Delete Manufacturer passed")

    def test_add_edit_delete_product(self):
        category = Category.objects.create(name='Supplements', low_stock_threshold=5)
        manufacturer = Manufacturer.objects.create(name='Vital Co')

        data = {
            'name': 'Zinc Tablets',
            'category': category.id,
            'manufacturer': manufacturer.id,
            'sale_price': 5.99,
            'description': 'For immune support'
        }
        name = data['name']
        response = self.client.post(reverse('add_product'), data, follow=True)
        obj = Product.objects.get(name='Zinc Tablets')
        self.assertActivityLog(self.user, "added new product", obj.id)
        self.assertMessagePresent(response, f"The product '{name}' added.")
        self.assertRedirects(response, reverse('product_list'))
        print("✅ Add Product passed")

        data['description'] = 'Updated info'
        response = self.client.post(reverse('edit_product', args=[obj.id]), data, follow=True)
        self.assertEqual(Product.objects.get(id=obj.id).description, 'Updated info')
        self.assertActivityLog(self.user, "edited product", obj.id)
        self.assertMessagePresent(response, f"The product '{name}' updated.")
        self.assertRedirects(response, reverse('product_list'))
        print("✅ Edit Product passed")

        response = self.client.post(reverse('delete_product', args=[obj.id]), follow=True)
        self.assertFalse(Product.objects.filter(id=obj.id).exists())
        self.assertActivityLog(self.user, "deleted product", obj.id)
        self.assertMessagePresent(response, f"The product '{name}' deleted.")
        self.assertRedirects(response, reverse('product_list'))
        print("✅ Delete Product passed")

    def test_add_edit_delete_customer(self):
        data = {
            'full_name': 'John Doe',
            'birthdate': '1985-01-01',
            'phone_number': '001-222-333-4444',
            'email': 'john.doe@example.com',
            'address': 'Main Street 42'
        }
        name = data['full_name']
        response = self.client.post(reverse('add_customer'), data, follow=True)
        obj = Customer.objects.get(full_name='John Doe')
        self.assertActivityLog(self.user, "added new customer", obj.id)
        self.assertMessagePresent(response, f"The customer '{name}' added.")
        self.assertRedirects(response, reverse('customer_list'))
        print("✅ Add Customer passed")

        data['address'] = 'New Address'
        response = self.client.post(reverse('edit_customer', args=[obj.id]), data, follow=True)
        self.assertEqual(Customer.objects.get(id=obj.id).address, 'New Address')
        self.assertActivityLog(self.user, "edited customer", obj.id)
        self.assertMessagePresent(response, f"The customer '{name}' updated.")
        self.assertRedirects(response, reverse('customer_list'))
        print("✅ Edit Customer passed")

        response = self.client.post(reverse('delete_customer', args=[obj.id]), follow=True)
        self.assertFalse(Customer.objects.filter(id=obj.id).exists())
        self.assertActivityLog(self.user, "deleted customer", obj.id)
        self.assertMessagePresent(response, f"The customer '{name}' deleted.")
        self.assertRedirects(response, reverse('customer_list'))
        print("✅ Delete Customer passed")
