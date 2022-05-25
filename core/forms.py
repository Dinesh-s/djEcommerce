import hashlib
from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from psqldb.models import UserTable
from django.contrib.auth.forms import UserCreationForm


PAYMENT_CHOICES = (
    ('S', 'Stripe'),
    ('P', 'PayPal')
)


class CheckoutForm(forms.Form):
    street = forms.CharField(required=True)
    area = forms.CharField(required=True)
    city = forms.CharField(required=True)
    zipcode = forms.CharField(required=True)

    payment_option = forms.ChoiceField(
        widget=forms.RadioSelect, choices=PAYMENT_CHOICES, required=True)


class CouponForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Promo code',
        'aria-label': 'Recipient\'s username',
        'aria-describedby': 'basic-addon2'
    }))


class RefundForm(forms.Form):
    ref_code = forms.CharField()
    message = forms.CharField(widget=forms.Textarea(attrs={
        'rows': 4
    }))
    email = forms.EmailField()


class PaymentForm(forms.Form):
    stripeToken = forms.CharField(required=False)
    save = forms.BooleanField(required=False)
    use_default = forms.BooleanField(required=False)


class ReigstrationForm(forms.ModelForm):
    USER_TYPE_CHOICES = (
        (1, 'I am A User'),
        (2, 'I am a Shopkeeper')
    )
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    email = forms.CharField(required=True)
    password = forms.CharField(widget=forms.PasswordInput())
    phone = forms.CharField(required=True)
    user_type = forms.ChoiceField(choices=USER_TYPE_CHOICES, widget=forms.RadioSelect)

    class Meta:
        model = UserTable
        fields = ("first_name", "last_name", "email", "password", "phone", "user_type")


class LoginForm(forms.ModelForm):
    email = forms.CharField(required=True)
    password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = UserTable
        fields = ("email", "password")


class ProductForm(forms.Form):
    CUSTOMIZABLE = (
        (1, True),
        (2, False)
    )
    name = forms.CharField(required=True)
    description = forms.CharField(required=True)
    image = forms.FileField()
    price = forms.DecimalField()
    customizable = forms.ChoiceField(choices=CUSTOMIZABLE, widget=forms.RadioSelect)