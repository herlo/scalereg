from django import forms
from django.db import models
from django.forms import ModelForm
from django.forms import ValidationError
from django.contrib.auth.models import User
from django.contrib.formtools.wizard import FormWizard
<<<<<<< HEAD:reg6/forms.py
#from models import Ticket,Item,Order,Payment
from models import Ticket,Item,Order

=======
from models import Ticket,Item,Order
#,Payment
>>>>>>> 473b1ff581f6b4676609fb95863c8bffb0b4271a:reg6/forms.py

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
<<<<<<< HEAD:reg6/forms.py

#    class Meta: 
#        model = Payment
#        fields = ('first_name', 'last_name', 'email')

class RegisterWizard(FormWizard):
	def done(self, request, form_list):
		return render_to_response('confirm.html', {
			'form_data': [form.cleaned_data for form in form_list],
		})

	def get_template(self, step):
		return 'reg6/regWizard_%s.html' % step
=======
#
#    class Meta: 
#        model = Payment
#        fields = ('first_name', 'last_name', 'email')
>>>>>>> 473b1ff581f6b4676609fb95863c8bffb0b4271a:reg6/forms.py
