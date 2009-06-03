from django.conf.urls.defaults import *
from scalereg.reg6.views import *
from scalereg.reg6.forms import TicketForm, ItemForm, OrderForm, PaymentForm
from django.contrib.auth.decorators import user_passes_test
from django.contrib.formtools.wizard import FormWizard

urlpatterns = patterns('scalereg.reg6.views',
    (r'^$', RegisterWizard([TicketForm, ItemForm, OrderForm, PaymentForm])),
)
