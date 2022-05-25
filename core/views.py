import hashlib
import random
import string

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, DetailView, View
from django.http import JsonResponse

from psqldb.models import OrderItemTable, OrderTable, PaymentTable, ProductTable, UserTable, addressTable


from .forms import CheckoutForm, CouponForm, LoginForm, ProductForm, RefundForm, PaymentForm, ReigstrationForm
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, UserProfile

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


def products(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "products.html", context)


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            items = self.request.session['cart']
            totalAmount = 0
            if 'cart' in self.request.session:
                for (index, item) in enumerate(self.request.session.get('cart')):
                    totalAmount = totalAmount + item['total']
            form = CheckoutForm()
            context = {
                'form': form,
                'items': items,
                'totalAmount': totalAmount,
                'DISPLAY_COUPON_FORM': False
            }
            return render(self.request, "checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        print(form)
        try:
            order = self.request.session['cart']
            if form.is_valid():
                self.request.session['address'] = {
                    'street': form.cleaned_data.get('street'),
                    'area': form.cleaned_data.get('area'),
                    'city': form.cleaned_data.get('city'),
                    'zipcode': form.cleaned_data.get('zipcode')
                }
                payment_option = form.cleaned_data.get('payment_option')

                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(
                        self.request, "Invalid payment option selected")
                    return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("core:order-summary")


class PaymentView(View):
    def get(self, *args, **kwargs):
        order = self.request.session['cart']
        if self.request.session['address']:
            context = {
                'items': order,
                'DISPLAY_COUPON_FORM': False,
                'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY
            }
            userprofile = self.request.session['user']
            # fetch the users card list
            # cards = stripe.Customer.list_sources(
            #     'cus_4QE4bx4C5BVSrC',
            #     limit=3,
            #     object='card'
            # )
            # card_list = cards['data']
            # if len(card_list) > 0:
            #     # update the context with the default card
            #     context.update({
            #         'card': card_list[0]
            #     })
            return render(self.request, "payment.html", context)
        else:
            messages.warning(
                self.request, "You have not added a billing address")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        order = self.request.session['cart']
        form = PaymentForm(self.request.POST)
        userprofile = self.request.session['user']
        if form.is_valid():
            token = form.cleaned_data.get('stripeToken')
            save = form.cleaned_data.get('save')
            use_default = form.cleaned_data.get('use_default')

            totalAmount = 0
            if 'cart' in self.request.session:
                for (index, item) in enumerate(self.request.session.get('cart')):
                    totalAmount = totalAmount + item['total']

            amount = int(totalAmount * 100)
            try:

                if use_default or save:
                    # charge the customer because we cannot charge the token more than once
                    charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="inr",
                        customer=userprofile.stripe_customer_id
                    )
                else:
                    # charge once off on the token
                    charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="inr",
                        source=token
                    )
                logUser = UserTable.objects.filter(user_uuid=userprofile['user_uuid'])[0]
                # create the payment
                payment = PaymentTable()
                payment.transaction_id = charge['id']
                payment.user = logUser
                payment.amount = totalAmount
                payment.status = 1
                payment.save()

                # assign the payment to the order

                # order_items = order.items.all()
                # order_items.update(ordered=True)
                # for item in order_items:
                #     item.save()

                # order.ordered = True
                # order.payment = payment
                # order.ref_code = create_ref_code()
                # order.save()
                payment = PaymentTable()
                payment.transaction_id = charge['id']
                payment.user = logUser
                payment.amount = totalAmount
                payment.status = 2
                payment.save()

                sessionAddr = self.request.session['address']
                address = addressTable()
                address.street = sessionAddr['street']
                address.area = sessionAddr['area']
                address.city = sessionAddr['city']
                address.zipcode = sessionAddr['zipcode']
                address.user = logUser
                address.save()

                orderData = OrderTable()
                orderData.user = logUser
                orderData.total = totalAmount
                orderData.shipping_address = address
                orderData.payment_id = payment
                orderData.save()

                for (index, item) in enumerate(self.request.session.get('cart')):
                    orderItem = OrderItemTable()
                    orderItem.order = orderData
                    orderItem.product = ProductTable.objects.filter(product_uuid=item['product_uuid'])[0]
                    orderItem.qty = item['qty']
                    orderItem.custom_text = item['customText']
                    orderItem.custom_image = item['customImage']
                    orderItem.save()
                self.request.session['cart'] = []
                messages.success(self.request, "Your order was successful!")
                return redirect("/")

            except stripe.error.CardError as e:
                body = e.json_body
                err = body.get('error', {})

                sessionAddr = self.request.session['address']
                address = addressTable()
                address.street = sessionAddr['street']
                address.area = sessionAddr['area']
                address.city = sessionAddr['city']
                address.zipcode = sessionAddr['zipcode']
                address.user = logUser
                address.save()

                orderData = OrderTable()
                orderData.user = logUser
                orderData.total = totalAmount
                orderData.shipping_address = address
                orderData.payment_id = payment
                orderData.save()

                for (index, item) in enumerate(self.request.session.get('cart')):
                    orderItem = OrderItemTable()
                    orderItem.order = orderData
                    orderItem.product = ProductTable.objects.filter(product_uuid=item['product_uuid'])[0]
                    orderItem.qty = item['qty']
                    orderItem.custom_text = item['customText']
                    orderItem.custom_image = item['customImage']
                    orderItem.save()
                
                messages.warning(self.request, f"{err.get('message')}")
                return redirect("/")

            except stripe.error.RateLimitError as e:
                # Too many requests made to the API too quickly
                messages.warning(self.request, "Rate limit error")
                return redirect("/")

            except stripe.error.InvalidRequestError as e:
                # Invalid parameters were supplied to Stripe's API
                print(e)
                messages.warning(self.request, "Invalid parameters")
                return redirect("/")

            except stripe.error.AuthenticationError as e:
                # Authentication with Stripe's API failed
                # (maybe you changed API keys recently)
                messages.warning(self.request, "Not authenticated")
                return redirect("/")

            except stripe.error.APIConnectionError as e:
                # Network communication with Stripe failed
                messages.warning(self.request, "Network error")
                return redirect("/")

            except stripe.error.StripeError as e:
                # Display a very generic error to the user, and maybe send
                # yourself an email
                messages.warning(
                    self.request, "Something went wrong. You were not charged. Please try again.")
                return redirect("/")

            except Exception as e:
                # send an email to ourselves
                messages.warning(
                    self.request, "A serious error occurred. We have been notifed.")
                return redirect("/")

        messages.warning(self.request, "Invalid data received")
        return redirect("/payment/stripe/")


class HomeView(View):
    def get(self, *args, **kwargs):
        vendor = self.request.session.get('user')
        context = {
            "items": [],
            "productForm": ProductForm(),
            "message": ''
        }
        products = ProductTable.objects.filter()
        context["items"] = products
        return render(self.request, "home.html", context)


class OrderSummaryView(View):
    def get(self, *args, **kwargs):
        try:
            totalAmount = 0
            if 'cart' in self.request.session:
                for (index, item) in enumerate(self.request.session.get('cart')):
                    totalAmount = totalAmount + item['total']
            context = {
                'items': self.request.session.get('cart'),
                'total': totalAmount
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("/")


class ItemDetailView(View):
    def get(self, *args, **kwargs):
        print(self.kwargs['slug'])
        try:
            context = {
                "item": ProductTable.objects.filter(product_uuid=self.kwargs['slug'])[0]
            }
            return render(self.request, "product.html", context)
        except Exception as e:
            return redirect('home/')


def add_to_cart(request, slug):
    item = ProductTable.objects.filter(product_uuid=slug)[0]
    formdata = request.POST
    print("form ", formdata)
    fileData = request.FILES
    customImage = ''
    if(fileData['customImage']):
        handle_uploaded_file(fileData['customImage'], 'order')
        customImage = 'order/' + fileData['customImage'].name
    product = {'product_uuid': str(item.product_uuid), 'name': item.name, 'image': item.image, 'price': float(item.price), 'qty': 1, 'total': float(item.price), 'customizable': formdata.get('customizable'), 'customText': formdata.get('customText'), 'customImage': customImage}
    if request.session['user_login']:
        print("user logged in")
    else:
        return redirect("core:login_form")

    print(product)
    if 'cart' in request.session:
        cartItems = request.session['cart']
        itemIndex = -1

        for (index, item) in enumerate(cartItems):
            if(item['product_uuid'] == product['product_uuid']):
                itemIndex = index
        print("item index", itemIndex)
        if(itemIndex == -1):
            cartItems.append(product)
            request.session['cart'] = cartItems
            return redirect('/')
        else:
            cartItems[itemIndex]['qty'] = cartItems[itemIndex]['qty'] + 1
            cartItems[itemIndex]['total'] = cartItems[itemIndex]['qty'] * cartItems[itemIndex]['price']
            request.session['cart'] = cartItems
            return redirect('/')

    else:
        print('else in cart')
        request.session['cart'] = [product]
        return redirect("core:order-summary")


def add_to_cart_single_item(request, slug):
    item = ProductTable.objects.filter(product_uuid=slug)[0]
    
    if 'cart' in request.session:
        cartItems = request.session['cart']
        itemIndex = -1

        for (index, item) in enumerate(cartItems):
            if(item['product_uuid'] == slug):
                itemIndex = index
        
        cartItems[itemIndex]['qty'] = cartItems[itemIndex]['qty'] + 1
        cartItems[itemIndex]['total'] = cartItems[itemIndex]['qty'] * cartItems[itemIndex]['price']
        
        request.session['cart'] = cartItems
        return redirect("core:order-summary")


def remove_from_cart(request, slug):
    item = ProductTable.objects.filter(product_uuid=slug)[0]
    if 'cart' in request.session:
        cartItems = request.session['cart']
        itemIndex = -1
        for (index, item) in enumerate(cartItems):
            if(item['product_uuid'] == slug):
                itemIndex = index
        if(itemIndex != -1):
            cartItems.remove(cartItems[itemIndex])
            request.session['cart'] = cartItems
    
    return redirect("core:order-summary")


def remove_single_item_from_cart(request, slug):
    item = ProductTable.objects.filter(product_uuid=slug)[0]
    if 'cart' in request.session:
        cartItems = request.session['cart']
        itemIndex = -1
        for (index, item) in enumerate(cartItems):
            if(item['product_uuid'] == slug):
                itemIndex = index
        if(itemIndex != -1):
            cartItems[itemIndex]['qty'] = cartItems[itemIndex]['qty'] - 1
            cartItems[itemIndex]['total'] = cartItems[itemIndex]['qty'] * cartItems[itemIndex]['price']
        print("cartItems[itemIndex]['qty']", cartItems[itemIndex]['qty'])
        if cartItems[itemIndex]['qty'] == 0:
            cartItems.remove(cartItems[itemIndex])
        request.session['cart'] = cartItems
    
    return redirect("core:order-summary")


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon")
                return redirect("core:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("core:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request was received.")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("core:request-refund")


class SignupForm(View):
    def get(self, *args, **kwargs):
        form = ReigstrationForm()
        context = {
            'form': form,
            'message': ""
        }
        return render(self.request, "account/signup.html", context)

    def post(self, *args, **kwargs):
        # order = Order.objects.get(user=self.request.user, ordered=False)
        formdata = self.request.POST
        print("hey", formdata)
        user = UserTable()
        user.first_name = formdata.get('first_name')
        user.last_name = formdata.get('last_name')
        user.email = formdata.get('email')
        user.password = hashlib.md5(formdata.get('password').encode('utf-8')).hexdigest()
        user.phone = formdata.get('phone')
        user.user_type = formdata.get('user_type')
        user.profile_pic = ""
        form = ReigstrationForm()
        context = {
            'form': form,
            'message': "test"
        }
        try:
            user.save()
            context['message'] = "Registration Success.! Please Login.!"

        except Exception as e:
            print("user registration", e)
            context['message'] = "Registration Failed.!"

        return render(self.request, "account/signup.html", context)


class LoginView(View):
    def get(self, *args, **kwargs):
        form = LoginForm()
        context = {
            'form': form,
            'message': ""
        }
        return render(self.request, "account/login.html", context)

    def post(self, *args, **kwargs):
        # order = Order.objects.get(user=self.request.user, ordered=False)
        formdata = self.request.POST
        result = hashlib.md5(formdata.get('password').encode('utf-8')).hexdigest()
        user = UserTable.objects.filter(email=formdata.get('email'), password=result)
        form = LoginForm()
        context = {
            'form': form,
            'message': ""
        }
        try:
            if(user):
                session_data = {
                    "user_uuid": str(user[0].user_uuid),
                    "first_name": user[0].first_name,
                    "last_name": user[0].last_name,
                    "email": user[0].email,
                    "phone": user[0].phone,
                    "user_type": user[0].user_type,
                    "verified": user[0].verified,
                    "created_at": str(user[0].created_at.utcnow()),
                    "profile_pic": user[0].profile_pic,
                    "cart_item_count": 0,
                    "is_authenticated": True
                }
                self.request.session['user'] = session_data
                self.request.session['user_login'] = True
                self.request.session['cart'] = []
                return redirect("/")
            else:
                context['message'] = "Login Failed.!"

        except Exception as e:
            print("user Login", e)
            context['message'] = "Login Failed.!"

        return render(self.request, "account/login.html", context)


class LogoutView(View):
    def get(self, *args, **kwargs):
        self.request.session['user'] = {}
        self.request.session['user_login'] = False
        self.request.session['cart'] = []
        return redirect("/")


class VendorAccountView(View):
    def get(self, *args, **kwargs):
        vendor = self.request.session.get('user')
        print(vendor['user_uuid'])
        context = {
            "items": [],
            "productForm": ProductForm(),
            "message": ''
        }
        products = ProductTable.objects.filter(vendor=vendor['user_uuid'])
        context["items"] = products
        return render(self.request, "vendor_account.html", context)

    def post(self, *args, **kwargs):
        # order = Order.objects.get(user=self.request.user, ordered=False)
        formdata = self.request.POST
        fileData = self.request.FILES
        handle_uploaded_file(fileData['image'], 'upload')
        print(formdata)
        product = ProductTable()
        product.name = formdata.get('name')
        product.description = formdata.get('description')
        product.image = 'upload/' + fileData['image'].name
        vendor = self.request.session.get('user')
        product.vendor = UserTable.objects.filter(user_uuid=vendor['user_uuid'])[0]
        product.price = formdata.get('price')
        context = {
            "items": [],
            "productForm": ProductForm(),
            "message": "Product Saved Successfully..!"
        }
        try:
            product.save()
            products = ProductTable.objects.filter(vendor=vendor['user_uuid'])
            context["items"] = products
            return render(self.request, "vendor_account.html", context)
        except Exception as e:
            context["message"] = "Product Add Failed..!"
            products = ProductTable.objects.filter(vendor=vendor['user_uuid'])
            context["items"] = products
            return render(self.request, "vendor_account.html", context)


class UserAccountView(View):
    def get(self, *args, **kwargs):
        user = self.request.session.get('user')
        print(user['user_uuid'])
        myorders = OrderTable.objects.filter(user=user['user_uuid'])
        context = {
            "orders": myorders,
            "message": ''
        }
        return render(self.request, "user_account.html", context)


class OrderDetailsView(View):
    def get(self, *args, **kwargs):
        try:
            print(self.kwargs['slug'])
            order = OrderTable.objects.filter(order_uuid=self.kwargs['slug'])[0]
            orderItems = OrderItemTable.objects.filter(order_id=self.kwargs['slug'])
            items = []
            for orderit in orderItems:
                print(orderit.product.name)
                items.append({
                    'name': orderit.product.name,
                    'customText': orderit.custom_text,
                    'customImage': orderit.custom_image,
                    'qty': orderit.qty,
                    'price': orderit.product.price,
                    'total': float(orderit.product.price) * float(orderit.qty)
                })

            payment = PaymentTable.objects.filter(payment_uuid=order.payment_id)
            context = {
                'order': order,
                'items': items,
                'payment': payment,
            }
            return render(self.request, 'order_details.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("/")


def handle_uploaded_file(f, foldername='upload'):
    with open('static_in_env/' + foldername + '/' + f.name, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
