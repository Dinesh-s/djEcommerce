from django.contrib import admin
from psqldb.models import UserTable, ProductTable, addressTable, PaymentTable, OrderTable, OrderItemTable, verificationTable
from django.contrib.auth.models import User

# Register your models here.

# admin.site.register(UserTable)
# admin.site.unregister(User)
admin.site.register(UserTable)
admin.site.register(ProductTable)
admin.site.register(addressTable)
admin.site.register(PaymentTable)
admin.site.register(OrderTable)
admin.site.register(OrderItemTable)
admin.site.register(verificationTable)