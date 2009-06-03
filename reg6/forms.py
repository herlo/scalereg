from django import forms
from django.db import models
from django.forms import ModelForm
from django.forms import ValidationError
from django.contrib.auth.models import User
from django.contrib.formtools.wizard import FormWizard
from models import Ticket,Item,Order
#,Payment

class TicketForm(forms.ModelForm):

    class Meta:
        model = Ticket
        fields = ('name', 'description', 'price')

class ItemForm(forms.ModelForm):

    class Meta:
        model = Item
        fields = ('name', 'description', 'price')

class OrderForm(forms.ModelForm):

    class Meta: 
        model = Order
        fields = ('first_name', 'last_name', 'email')

#class PaymentForm(forms.ModelForm):
#
#    class Meta: 
#        model = Payment
#        fields = ('first_name', 'last_name', 'email')
