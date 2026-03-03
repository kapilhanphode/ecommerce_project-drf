from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
from store.models import Order


class OrderAPITest(APITestCase):

    def setUp(self):
        # Create normal user
        self.user = User.objects.create_user(
            username="kapil",
            password="test123"
        )

        # Create admin user
        self.admin = User.objects.create_user(
            username="admin",
            password="admin123",
            is_staff=True
        )

        # Create one order for normal user
        self.order = Order.objects.create(
            user=self.user,
            status="pending"
        )

    # ✅ Test Order List
    def test_user_can_list_orders(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("orders-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ✅ Test Order Creation
    def test_user_can_create_order(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("orders-list")
        data = {
            "status": "pending"
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 2)

    # ✅ Test Custom Action: Pay
    def test_pay_action_success(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("orders-pay", args=[self.order.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "success")

    # ✅ Test Pay Again (Already Processed)
    def test_pay_action_already_processed(self):
        self.order.status = "success"
        self.order.save()

        self.client.force_authenticate(user=self.user)

        url = reverse("orders-pay", args=[self.order.id])
        response = self.client.post(url)

        self.assertEqual(response.data["message"], "Already Processed")

    # ✅ Test Delete Permission (Normal User Should Fail)
    def test_normal_user_cannot_delete(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("orders-detail", args=[self.order.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_cancelled_order(self):
        self.client.force_authenticate(user=self.admin)

        # Change order status to cancelled
        self.order.status = "cancelled"
        self.order.save()

        url = reverse("orders-detail", args=[self.order.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_admin_cannot_delete_pending_order(self):
        self.client.force_authenticate(user=self.admin)

        self.order.status = "pending"
        self.order.save()

        url = reverse("orders-detail", args=[self.order.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)