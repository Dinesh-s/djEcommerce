from asyncio.windows_events import NULL
import uuid
from django.db import models
from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser
)


class UserTable (models.Model):
    USER_TYPE_CHOICES = (
        (1, 'user'),
        (2, 'vendor'),
        (3, 'admin')
    )
    USER_VERIFIED = (
        (1, 'verified'),
        (2, 'not-verified')
    )
    user_uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    password = models.CharField(max_length=200)
    phone = models.CharField(max_length=200)
    user_type = models.PositiveSmallIntegerField(choices=USER_TYPE_CHOICES, default=1)
    verified = models.PositiveSmallIntegerField(choices=USER_VERIFIED, default=2)
    created_at = models.DateTimeField(auto_now=True)
    profile_pic = models.CharField(max_length=200)


class ProductTable(models.Model):
    CUSTOMIZABLE = (
        (1, True),
        (2, False)
    )
    product_uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200)
    image = models.CharField(max_length=200)
    vendor = models.ForeignKey(UserTable, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    customizable = models.PositiveSmallIntegerField(choices=CUSTOMIZABLE, default=2)


class addressTable(models.Model):
    address_uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    street = models.CharField(max_length=200)
    area = models.CharField(max_length=200)
    city = models.CharField(max_length=200)
    zipcode = models.CharField(max_length=10)
    user = models.ForeignKey(UserTable, on_delete=models.CASCADE)


class PaymentTable(models.Model):
    STATUS_CODE = (
        (1, 'SUCCESS'),
        (2, 'FAILED')
    )
    payment_uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_id = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(UserTable, on_delete=models.CASCADE)
    status = models.PositiveSmallIntegerField(choices=STATUS_CODE)


class OrderTable(models.Model):
    STATUS_CODE = (
        (1, 'PENDING'),
        (2, 'DONE')
    )
    order_uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserTable, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    order_date = models.DateTimeField(auto_now=True)
    delivered = models.PositiveSmallIntegerField(choices=STATUS_CODE, default=1)
    shipped = models.PositiveSmallIntegerField(choices=STATUS_CODE, default=1)
    shipping_address = models.ForeignKey(addressTable, on_delete=models.CASCADE)
    payment_id = models.ForeignKey(PaymentTable, on_delete=models.CASCADE)


class OrderItemTable(models.Model):
    order_item_uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(OrderTable, on_delete=models.CASCADE)
    product = models.ForeignKey(ProductTable, on_delete=models.CASCADE)
    qty = models.CharField(max_length=200)
    custom_text = models.CharField(max_length=200, default=NULL)
    custom_image = models.CharField(max_length=200, default=NULL)


class verificationTable(models.Model):
    STATUS_CODE = (
        (1, 'PENDING'),
        (2, 'DONE')
    )
    verification_uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(UserTable, on_delete=models.CASCADE, null=True, related_name='creator')
    type_of_doc = models.CharField(max_length=200)
    document_url = models.CharField(max_length=200)
    verified = models.PositiveSmallIntegerField(choices=STATUS_CODE, default=1)
    verified_by = models.ForeignKey(UserTable, on_delete=models.CASCADE, null=True, related_name='admin')
    uploaded_date = models.DateTimeField()
    verified_date = models.DateTimeField()
