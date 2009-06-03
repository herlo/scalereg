from django.conf.urls.defaults import *
from scalereg.reg6.views import *
<<<<<<< HEAD:reg6/urls.py
#from scalereg.reg6.forms import TicketForm, ItemForm, OrderForm, PaymentForm
from scalereg.reg6.forms import TicketForm, ItemForm, OrderForm, RegisterWizard
=======
from scalereg.reg6.forms import TicketForm, ItemForm, OrderForm
>>>>>>> 473b1ff581f6b4676609fb95863c8bffb0b4271a:reg6/urls.py
from django.contrib.auth.decorators import user_passes_test
from django.contrib.formtools.wizard import FormWizard

urlpatterns = patterns('scalereg.reg6.views',
<<<<<<< HEAD:reg6/urls.py
#    (r'^$', RegisterWizard([TicketForm, ItemForm, OrderForm, PaymentForm])),
    (r'^$', RegisterWizard([TicketForm, ItemForm, OrderForm])),

=======
    (r'^$', RegisterWizard([TicketForm, ItemForm, OrderForm])),
>>>>>>> 473b1ff581f6b4676609fb95863c8bffb0b4271a:reg6/urls.py
)
