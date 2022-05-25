from django.urls import path

from .views import (
    ItemDetailView,
    CheckoutView,
    HomeView,
    LoginView,
    LogoutView,
    OrderDetailsView,
    OrderSummaryView,
    SignupForm,
    LoginForm,
    UserAccountView,
    VendorAccountView,
    add_to_cart,
    add_to_cart_single_item,
    remove_from_cart,
    remove_single_item_from_cart,
    PaymentView,
    AddCouponView,
    RequestRefundView
)

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('product/<slug>/', ItemDetailView.as_view(), name='product'),
    path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
    path('add-single-item-to-cart/<slug>/', add_to_cart_single_item, name='add-single-item-to-cart'),
    path('add-coupon/', AddCouponView.as_view(), name='add-coupon'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('remove-item-from-cart/<slug>/', remove_single_item_from_cart,
         name='remove-single-item-from-cart'),
    path('payment/<payment_option>/', PaymentView.as_view(), name='payment'),
    path('request-refund/', RequestRefundView.as_view(), name='request-refund'),
    path('signup/', SignupForm.as_view(), name="sign_up_form"),
    path('login/', LoginView.as_view(), name="login_form"),
    path('logout/', LogoutView.as_view(), name="logout"),

    path('vedor/account/', VendorAccountView.as_view(), name="vendor_account"),
    path('user/account/', UserAccountView.as_view(), name="user_account"),
    path('order-details/<slug>/', OrderDetailsView.as_view(), name='order_details'),
]