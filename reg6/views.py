# Create your views here.

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail, mail_managers
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render_to_response

import datetime
import random
import re
import string
import sys
import decimal

from scale.paypal import Endpoint

import models # relative import

DEBUG_LOGGING = False
STEPS_TOTAL = 7

def ScaleDebug(msg):
  if not DEBUG_LOGGING:
    return

  frame = sys._getframe(1)

  name = frame.f_code.co_name
  line_number = frame.f_lineno
  filename = frame.f_code.co_filename

  line = 'File "%s", line %d, in %s: %s' % (filename, line_number, name, msg)
  handle = open('/tmp/scale_reg.log', 'a')
  handle.write("%s: %s\n" % (datetime.datetime.now(), line))
  handle.close()


def PrintAttendee(attendee):
  badge = []
  badge.append(attendee.salutation)
  badge.append(attendee.first_name)
  badge.append(attendee.last_name)
  badge.append(attendee.title)
  badge.append(attendee.org)
  badge.append(attendee.email)
  badge.append(attendee.phone)
  badge.append(str(attendee.id))
  badge.append(attendee.badge_type.type)
  if not attendee.order:
    return ''
  if attendee.order.payment_type in ('verisign', 'google', 'cash'):
    badge.append("%2.2f" % attendee.ticket_cost())
  else:
    badge.append('0.00')

  tshirt = attendee.answers.filter(question='What is your shirt size?')
  if tshirt:
    badge.append(tshirt[0].text)
  else:
    badge.append('???')

  for i in attendee.ordered_items.all():
    badge.append(i.name)

  return '~' + '~'.join([x.replace('~', '') for x in badge]) + '~'


def ApplyPromoToTickets(promo, tickets):
  if not promo:
    return None
  for t in tickets:
    if promo.is_applicable_to(t):
      t.price *= promo.price_modifier
  return promo.name


def ApplyPromoToItems(promo, items):
  if not promo:
    return None
  for item in items:
    if item.promo:
      item.price *= promo.price_modifier
  return promo.name


def GetTicketItems(ticket):
  set1 = ticket.item_set.all()
  set2 = models.Item.objects.filter(applies_to_all=True)
  combined_set = [ s for s in set1 if s.active ]
  for s in set2:
    if not s.active:
      continue
    if s not in combined_set:
      combined_set.append(s)
  combined_set.sort()
  return combined_set


def CheckVars(request, post, cookies):
  for var in post:
    if var not in request.POST:
      return scale_render_to_response(request, 'reg6/reg_error.html',
        {'title': 'Registration Problem',
         'error_message': 'No %s information.' % var,
        })
  for var in cookies:
    if var not in request.session:
      return scale_render_to_response(request, 'reg6/reg_error.html',
        {'title': 'Registration Problem',
         'error_message': 'No %s information.' % var,
        })
  return None


def GenerateOrderID(bad_nums):
  valid_chars = string.ascii_uppercase + string.digits
  id = ''.join([random.choice(valid_chars) for x in xrange(10)])
  if not bad_nums:
    return id
  while id in bad_nums:
    id = ''.join([random.choice(valid_chars) for x in xrange(10)])
  return id


def scale_render_to_response(request, template, vars):
  if 'kiosk' in request.session:
    vars['kiosk'] = True
  return render_to_response(template, vars)


def index(request):
  avail_tickets = models.Ticket.public_objects.order_by('description')
  active_promocode_set = models.PromoCode.active_objects
  avail_promocodes = active_promocode_set.names()

  kiosk_mode = False
  promo_in_use = None
  if request.method == 'GET':
    if 'promo' in request.GET and request.GET['promo'] in avail_promocodes:
      promo_in_use = active_promocode_set.get(name=request.GET['promo'])
    if 'kiosk' in request.GET:
      kiosk_mode = True
  elif request.method == 'POST':
    if 'promo' in request.POST and request.POST['promo'] in avail_promocodes:
      promo_in_use = active_promocode_set.get(name=request.POST['promo'])

  promo_name = ApplyPromoToTickets(promo_in_use, avail_tickets)

  request.session.set_test_cookie()

  if kiosk_mode:
    request.session['kiosk'] = True
    return render_to_response('reg6/reg_kiosk.html')

  return scale_render_to_response(request, 'reg6/reg_index.html',
    {'title': 'Registration',
     'tickets': avail_tickets,
     'promo': promo_name,
     'step': 1,
     'steps_total': STEPS_TOTAL,
    })

def clear_kiosk(request):
    if request.session.get('kiosk', None) != None:
        del request.session['kiosk']

    return HttpResponseRedirect("/utoscreg/")

def kiosk_index(request):
  response = HttpResponse()
  response.write("""<html><head></head>
  <body>
  <div align="center">
  <h1>Welcome to SCALE 6X</h1>
  <h1>February 8 - 10, 2008</h1>

  <hr noshade width="60%">

  <h1>Please make a selection below:</h1>

  <table border="0" cellpadding="4">
  <tr>
  <td valign="top">
  <form method="get" action="../checkin/">
  <input type="submit" value="&nbsp;&nbsp;Check In&nbsp;&nbsp;">
  <input type="hidden" name="kiosk" value="0">
  </form>
  </td>
  <td valign="top">
  If you already registered with SCALE<br />
  and would like to pick up your badge.
  </td>
  </tr>
  <tr>
  <td valign="top">
  <form method="get" action="../">
  <input type="submit" value="Registration">
  <input type="hidden" name="kiosk" value="0">
  </form>
  </td>
  <td valign="top">If you have not registered with SCALE.</td>
  </tr>
  </table>

  <p>If you are a speaker, exhibitor, or a member of the press, please go to
  the registration desk.</p>
  </div></body></html>""")
  return response


def AddItems(request):
  if request.method != 'POST':
    return HttpResponseRedirect('/utoscreg/')
  if 'HTTP_REFERER' not in request.META or \
    '/utoscreg/' not in request.META['HTTP_REFERER']:
    return HttpResponseRedirect('/utoscreg/')

  required_vars = ['promo', 'ticket']
  r = CheckVars(request, required_vars, [])
  if r:
    return r

  ticket = models.Ticket.public_objects.filter(name=request.POST['ticket'])
  active_promocode_set = models.PromoCode.active_objects
  avail_promocodes = active_promocode_set.names()

  promo = request.POST['promo'].upper()
  promo_in_use = None
  if promo in avail_promocodes:
    promo_in_use = active_promocode_set.get(name=promo)

  promo_name = ApplyPromoToTickets(promo_in_use, ticket)
  items = GetTicketItems(ticket[0])
  ApplyPromoToItems(promo_in_use, items)

  return scale_render_to_response(request, 'reg6/reg_items.html',
    {'title': 'Registration - Add Items',
     'ticket': ticket[0],
     'promo': promo_name,
     'items': items,
     'step': 2,
     'steps_total': STEPS_TOTAL,
    })


def AddAttendee(request):
  if request.method != 'POST':
    return HttpResponseRedirect('/utoscreg/')

  action = None
  if 'HTTP_REFERER' in request.META:
    if '/utoscreg/add_items/' in request.META['HTTP_REFERER']:
      action = 'add'
    elif '/utoscreg/add_attendee/' in request.META['HTTP_REFERER']:
      action = 'check'

  if not action:
    return HttpResponseRedirect('/utoscreg/')

  required_vars = ['ticket', 'promo']
  r = CheckVars(request, required_vars, [])
  if r:
    return r

  ticket = models.Ticket.public_objects.filter(name=request.POST['ticket'])
  active_promocode_set = models.PromoCode.active_objects
  avail_promocodes = active_promocode_set.names()

  promo_in_use = None
  if request.POST['promo'] in avail_promocodes:
    promo_in_use = active_promocode_set.get(name=request.POST['promo'])

  promo_name = ApplyPromoToTickets(promo_in_use, ticket)
  avail_items = GetTicketItems(ticket[0])

  selected_items = []
  for i in xrange(len(avail_items)):
    item_number = 'item%d' % i
    if item_number in request.POST:
      item = models.Item.objects.get(name=request.POST[item_number])
      if item in avail_items:
        selected_items.append(item)
  ApplyPromoToItems(promo_in_use, selected_items)

  total = ticket[0].price
  for item in selected_items:
    total += item.price

  questions = []
  all_active_questions = models.Question.objects.filter(active=True)
  for q in all_active_questions:
    if q.applies_to_all or ticket[0] in q.applies_to_tickets.all():
      questions.append(q)
    else:
      for item in selected_items:
        if item in q.applies_to_items.all():
          questions.append(q)
          break

  manipulator = models.Attendee.AddManipulator()

  if action == 'add':
    errors = new_data = {}
  else:
    new_data = request.POST.copy()

    # add badge type
    new_data['badge_type'] = new_data['ticket']
    # add ordered items
    for s in selected_items:
      new_data.appendlist('ordered_items', str(s.id))
    # add promo
    if new_data['promo'] == 'None':
      new_data['promo'] = ''
    # add other fields
    new_data['obtained_items'] = new_data['survey_answers'] = ''
    # add survey answers

    for i in xrange(len(questions)):
      i = 'q%d' % i
      if i in request.POST:
        try:
          ans = models.Answer.objects.get(id=request.POST[i])
        except models.Answer.DoesNotExist:
          continue
        new_data.appendlist('answers', request.POST[i])

    try:
      errors = manipulator.get_validation_errors(new_data)
    except: # FIXME sometimes we get an exception, not sure how to reproduce
      return scale_render_to_response(request, 'reg6/reg_error.html',
        {'title': 'Registration Problem',
         'error_message': 'An unexpected error occurred, please try again.'
        })
    if not errors:
      if not request.session.test_cookie_worked():
        return scale_render_to_response(request, 'reg6/reg_error.html',
          {'title': 'Registration Problem',
           'error_message': 'Please do not register multiple attendees at the same time. Please make sure you have cookies enabled.',
          })
      request.session.delete_test_cookie()
      manipulator.do_html2python(new_data)
      new_place = manipulator.save(new_data)
      request.session['attendee'] = new_place.id

      # add attendee to order
      if 'payment' not in request.session:
        request.session['payment'] = [new_place.id]
      else:
        request.session['payment'].append(new_place.id)

      return HttpResponseRedirect('/utoscreg/registered_attendee/')

  form = forms.FormWrapper(manipulator, new_data, errors)
  return scale_render_to_response(request, 'reg6/reg_attendee.html',
    {'title': 'Register Attendee',
     'ticket': ticket[0],
     'promo': promo_name,
     'items': selected_items,
     'total': total,
     'questions': questions,
     'form': form,
     'step': 3,
     'steps_total': STEPS_TOTAL,
    })


def RegisteredAttendee(request):
  if request.method != 'GET':
    return HttpResponseRedirect('/utoscreg/')
  if 'HTTP_REFERER' not in request.META  or \
    '/utoscreg/add_attendee/' not in request.META['HTTP_REFERER']:
    return HttpResponseRedirect('/utoscreg/')

  required_cookies = ['attendee']
  r = CheckVars(request, [], required_cookies)
  if r:
    return r

  attendee = models.Attendee.objects.get(id=request.session['attendee'])

  return scale_render_to_response(request, 'reg6/reg_finish.html',
    {'title': 'Attendee Registered',
     'attendee': attendee,
     'step': 4,
     'steps_total': STEPS_TOTAL,
    })


def StartPayment(request):
  PAYMENT_STEP = 5

  if 'payment' not in request.session:
    request.session['payment'] = []

  new_attendee = None
  all_attendees = []
  bad_attendee = None
  paid_attendee = None
  removed_attendee = None
  total = 0

  # sanitize session data first
  for id in request.session['payment']:
    try:
      person = models.Attendee.objects.get(id=id)
    except models.Attendee.DoesNotExist:
      continue
    if not person.valid:
      all_attendees.append(id)

  if 'remove' in request.POST:
    try:
      remove_id = int(request.POST['remove'])
      if remove_id in all_attendees:
        all_attendees.remove(remove_id)
    except ValueError:
      pass
  elif 'id' in request.POST and 'email' in request.POST:
    try:
      id = int(request.POST['id'])
      new_attendee = models.Attendee.objects.get(id=id)
    except (ValueError, models.Attendee.DoesNotExist):
      id = None

    if id in all_attendees:
      new_attendee = None
    elif new_attendee and new_attendee.email == request.POST['email']:
      if not new_attendee.valid:
        if new_attendee not in all_attendees:
          all_attendees.append(id)
      else:
        paid_attendee = new_attendee
        new_attendee = None
    else:
      bad_attendee = [request.POST['id'], request.POST['email']]
      new_attendee = None

  # sanity check
  checksum = 0
  for f in [new_attendee, bad_attendee, paid_attendee, removed_attendee]:
    if f:
      checksum += 1
  assert checksum <= 1

  all_attendees_data = []
  for id in all_attendees:
    try:
      attendee = models.Attendee.objects.get(id=id)
      if not attendee.valid:
        all_attendees_data.append(attendee)
    except models.Attendee.DoesNotExist:
      pass

  all_attendees = [attendee.id for attendee in all_attendees_data]

  request.session['payment'] = all_attendees
  for person in all_attendees_data:
    total += person.ticket_cost()

  return scale_render_to_response(request, 'reg6/reg_start_payment.html',
    {'title': 'Place Your Order',
     'bad_attendee': bad_attendee,
     'new_attendee': new_attendee,
     'paid_attendee': paid_attendee,
     'removed_attendee': removed_attendee,
     'attendees': all_attendees_data,
     'step': PAYMENT_STEP,
     'steps_total': STEPS_TOTAL,
     'total': total,
    })


def Payment(request):
  PAYMENT_STEP = 6

  if request.method != 'POST':
    return HttpResponseRedirect('/utoscreg/')
  if 'HTTP_REFERER' not in request.META  or \
    '/utoscreg/start_payment/' not in request.META['HTTP_REFERER']:
    return HttpResponseRedirect('/utoscreg/')

  required_cookies = ['payment']
  r = CheckVars(request, [], required_cookies)
  if r:
    return r

  total = 0

  all_attendees = request.session['payment']
  all_attendees_data = []
  for id in all_attendees:
    try:
      attendee = models.Attendee.objects.get(id=id)
      if not attendee.valid:
        all_attendees_data.append(attendee)
    except models.Attendee.DoesNotExist:
      pass

  all_attendees = [attendee.id for attendee in all_attendees_data]
  request.session['payment'] = all_attendees

  for person in all_attendees_data:
    total += person.ticket_cost()

  csv = ','.join([str(x) for x in all_attendees])

  order_tries = 0
  order_saved = False
  while not order_saved:
    try:
      bad_order_nums = [ x.order_num for x in models.TempOrder.objects.all() ]
      bad_order_nums += [ x.order_num for x in models.Order.objects.all() ]
      order_num = GenerateOrderID(bad_order_nums)
      temp_order = models.TempOrder(order_num=order_num, attendees=csv)
      temp_order.save()
      order_saved = True
    except: # FIXME catch the specific db exceptions
      order_tries += 1
      if order_tries > 10:
        return scale_render_to_response(request, 'reg6/reg_error.html',
          {'title': 'Registration Problem',
           'error_message': 'We cannot generate an order ID for you.',
          })

  return scale_render_to_response(request, 'reg6/reg_payment.html',
    {'title': 'Registration Payment',
     'attendees': all_attendees_data,
     'order': order_num,
     'step': PAYMENT_STEP,
     'steps_total': STEPS_TOTAL,
     'total': total,
    })


def Sale(request):
  if request.method != 'POST':
    ScaleDebug('not POST')
    return HttpResponseServerError('not POST')
  if 'HTTP_REFERER' in request.META:
    print request.META['HTTP_REFERER']
  if 'HTTP_REFERER' not in request.META  or \
    '/utoscreg/start_payment/' not in request.META['HTTP_REFERER']:
    return HttpResponseRedirect('/utoscreg/')

  ScaleDebug(request.META)
  ScaleDebug(request.POST)

  required_vars = [
      'NAME',
      'ADDRESS',
      'CITY',
      'STATE',
      'ZIP',
      'COUNTRY',
      'PHONE',
      'EMAIL',
      'AMOUNT',
      'AUTHCODE',
      'RESULT',
      'RESPMSG',
      'USER1',
      'USER2',
  ]

  r = CheckVars(request, required_vars, [])
  if r:
    ScaleDebug('required vars missing')
    return HttpResponseServerError('required vars missing')
  if request.POST['RESULT'] != "0":
    ScaleDebug('transaction did not succeed')
    return HttpResponseServerError('transaction did not succeed')
  if request.POST['RESPMSG'] != "Approved":
    ScaleDebug('transaction declined')
    return HttpResponseServerError('transaction declined')

  try:
    temp_order = models.TempOrder.objects.get(order_num=request.POST['USER1'])
  except models.TempOrder.DoesNotExist:
    ScaleDebug('cannot get temp order')
    return HttpResponseServerError('cannot get temp order')

  order_exists = True
  try:
    order = models.Order.objects.get(order_num=request.POST['USER1'])
  except models.Order.DoesNotExist:
    order_exists = False
  if order_exists:
    ScaleDebug('order already exists')
    return HttpResponseServerError('order already exists')

  all_attendees_data = []
  for id in temp_order.attendees_list():
    try:
      attendee = models.Attendee.objects.get(id=id)
      if not attendee.valid:
        all_attendees_data.append(attendee)
    except models.Attendee.DoesNotExist:
      ScaleDebug('cannot find an attendee')
      return HttpResponseServerError('cannot find an attendee')

  total = 0
  for person in all_attendees_data:
    total += person.ticket_cost()
  assert int(total) == int(float(request.POST['AMOUNT']))

  try:
    order = models.Order(order_num=request.POST['USER1'],
      valid=True,
      name=request.POST['NAME'],
      address=request.POST['ADDRESS'],
      city=request.POST['CITY'],
      state=request.POST['STATE'],
      zip=request.POST['ZIP'],
      country=request.POST['COUNTRY'],
      email=request.POST['EMAIL'],
      phone=request.POST['PHONE'],
      amount=float(request.POST['AMOUNT']),
      payment_type='verisign',
      auth_code=request.POST['AUTHCODE'],
      resp_msg=request.POST['RESPMSG'],
      result=request.POST['RESULT'],
    )
    order.save()
  except Exception, inst: # FIXME catch the specific db exceptions
    ScaleDebug('cannot save order')
    print inst
    ScaleDebug(inst.args)
    ScaleDebug(inst)
    return HttpResponseServerError('cannot save order')

  for person in all_attendees_data:
    person.valid = True
    person.order = order
    if request.POST['USER2'] == 'Y':
      person.checked_in = True
    person.save()

  return HttpResponse('success')


def FailedPayment(request):
  return scale_render_to_response(request, 'reg6/reg_failed.html',
    {'title': 'Registration Payment Failed',
    })


def FinishPayment(request):
  PAYMENT_STEP = 7

  if request.method != 'POST':
    return HttpResponseRedirect('/utoscreg/')
#  if 'HTTP_REFERER' not in request.META  or \
#    '/utoscreg/start_payment/' not in request.META['HTTP_REFERER']:
#    return HttpResponseRedirect('/utoscreg/')

  required_vars = [
    'address_name',
    'payer_email',
    'mc_gross',
    'invoice', 
  ]

  r = CheckVars(request, required_vars, [])
  if r:
    return r

  try:
    print "Invoice: " + request.POST['invoice']
    order = models.Order.objects.get(order_num=request.POST['invoice'])
    all_attendees_data = models.Attendee.objects.filter(order=order.order_num)
  except models.Order.DoesNotExist:
    try:
        order = models.TempOrder.objects.get(order_num=request.POST['invoice'])
        attendee_list = order.attendees_list()
        all_attendees_data = list()
        for attendee in attendee_list:
            print "attendee: " + str(attendee)
            all_attendees_data.append(models.Attendee.objects.get(id=attendee))
    except models.TempOrder.DoesNotExist:
        ScaleDebug('Your order cannot be found')
        return HttpResponseServerError('Your order cannot be found')


  return scale_render_to_response(request, 'reg6/reg_receipt.html',
    {'title': 'Registration Payment Receipt',
     'name': request.POST['address_name'],
     'email': request.POST['payer_email'],
     'attendees': all_attendees_data,
     'order': request.POST['invoice'],
     'step': PAYMENT_STEP,
     'steps_total': STEPS_TOTAL,
     'total': request.POST['mc_gross'],
    })


class HandleIPN(Endpoint):
  """Handle IPN messages sent from PayPal once a user completes payment."""
  class PayPalException(Exception):

    def __init__(self, message):
      self.message = message

      mail_managers('PayPal IPN Error!', """The site encountered the
          following error with a PayPal IPN message. Please investigate.

          %s""" % message)

    def __str__(self):
      return repr(self.message)

  class InvalidPayPalResponse(PayPalException):
    """Raise this when PayPal returns an error. This is *not* the same as a
    failed credit card number/address/other-data, this is some kind of
    programmatic error.

    """
    pass

  class OrderUnknown(PayPalException):
    """Raise this when PayPal notifies us of an order that is not in our DB."""
    pass

  class OrderMismatch(PayPalException):
    """Raise this when PayPal notifies us of an order we know about, but the
    data doesn't match up.

    """
    pass

  def process(self, data):
    """Notification from PayPal that the transaction went through, didn't go
    through, or may be going through later.

    It is important to double-check the price, invoice, payer_email, and any
    other important data coming from PayPal to make sure that no tampering has
    been done since we first sent the user off to PayPal.

    We should update the existing entry in the database and email the user
    that the registration payment is complete.

    """
    # Make sure PayPal isn't sending us an order we've already processed
    # due to lag/mistake/act-of-god
    try:
      models.Order.objects.get(auth_code=data.get('txn_id'))
      return HttpResponse("Alright")
    except models.Order.DoesNotExist:
      pass

    try:
      temp_order = models.TempOrder.objects.get(order_num=data.get('invoice'))
    except models.TempOrder.DoesNotExist:
      raise HandleIPN.OrderUnknown("PayPal sent notification of an order from "\
            "%s that we do not have a record of." % data.get('payer_email'))

    # Check the PayPal order data against our own
    total = decimal.Decimal(str(data.get('mc_gross'))).quantize(models.TempOrder.TWOPLACES)
    if total != temp_order.total():
      raise HandleIPN.OrderMismatch(
          "The details for order %s don't match our database." % data.get('invoice'))

    if data.get('payment_status') == 'Completed':
      # Looks ok, make a real order and notify the user
      obj_dict = {
        'order_num': data.get('invoice'),
        'name': " ".join([data.get('first_name'), data.get('last_name')]),
        'address':  '',
        'city': '',
        'state': '',
        'zip': '',
        'country': '',
        'email': data.get('payer_email'),
        'phone': '',
        'amount': float(total),
        'payment_type': 'paypal',
        'auth_code': data.get('txn_id'),
      }

      order = models.Order.objects.create(**obj_dict)

      # Associate all the attendees with this order
      for i in models.Attendee.objects.filter(
          id__in=temp_order.attendees_list()):
        i.order = order
        i.save()

      send_mail('Your order is complete', """Congrats, your registration is
            complete, payed for, and we love you (now).""",
            settings.DEFAULT_FROM_EMAIL, [data.get('payer_email')])

    elif data.get('payment_status') == 'Failed':
      # Notify the user that payment did not go through
      send_mail('Your order is not complete', """Crap! There was a problem
            processing your order, please log in and try again.""",
            settings.DEFAULT_FROM_EMAIL, [data.get('payer_email')])

    elif data.get('payment_status') == 'Pending':
      # We don't care, PayPal will send another message when it's done
      pass

    return HttpResponse("Ok")

  def process_invalid(self, data):
    """Something bad and unexpected happened; PayPal was hacked, alien
    invasion forces are interfering with the signal, this IPN postback code
    doesn't work, etc.  This will require manual investigation.

    """
    # This should probably be logged somewhere with the ``data`` dictionary
    raise HandleIPN.InvalidPayPalResponse("Something is borked: " + str(data))


def RegLookup(request):
  if request.method != 'POST':
    return scale_render_to_response(request, 'reg6/reg_lookup.html',
      {'title': 'Registration Lookup',
      })

  required_vars = [
    'email',
    'zip',
  ]

  r = CheckVars(request, required_vars, [])
  if r:
    return r

  attendees = []
  if request.POST['zip'] and request.POST['email']:
    attendees = models.Attendee.objects.filter(zip=request.POST['zip'],
      email=request.POST['email'])

  return scale_render_to_response(request, 'reg6/reg_lookup.html',
    {'title': 'Registration Lookup',
     'attendees': attendees,
     'email': request.POST['email'],
     'zip': request.POST['zip'],
     'search': 1,
    })


def CheckIn(request):
  kiosk_mode = False
  if request.method == 'GET':
    if 'kiosk' in request.GET:
      request.session['kiosk'] = True
      return render_to_response('reg6/reg_kiosk.html')

    return scale_render_to_response(request, 'reg6/reg_checkin.html',
      {'title': 'Check In',
      })

  attendees = []
  attendees_email = []
  attendees_zip = []
  if request.POST['zip'] and request.POST['email']:
    attendees = models.Attendee.objects.filter(valid=True, checked_in=False,
      zip=request.POST['zip'],
      email=request.POST['email'])
  if not attendees:
    if request.POST['first'] and request.POST['last']:
      attendees = models.Attendee.objects.filter(valid=True, checked_in=False,
        first_name=request.POST['first'],
        last_name=request.POST['last'])
    if attendees:
      if request.POST['email']:
        attendees_email = attendees.filter(email=request.POST['email'])
      if request.POST['zip']:
        attendees_zip = attendees.filter(zip=request.POST['zip'])
      if attendees_email:
        attendees = attendees_email
      elif attendees_zip:
        attendees = attendees_zip

  return scale_render_to_response(request, 'reg6/reg_checkin.html',
    {'title': 'Check In',
     'attendees': attendees,
     'first': request.POST['first'],
     'last': request.POST['last'],
     'email': request.POST['email'],
     'zip': request.POST['zip'],
     'search': 1,
    })


def FinishCheckIn(request):
  if request.method != 'POST':
    return HttpResponseRedirect('/utoscreg/')

  required_vars = [
    'id',
  ]

  r = CheckVars(request, required_vars, [])
  if r:
    return r

  try:
    attendee = models.Attendee.objects.get(id=request.POST['id'])
  except models.Attendee.DoesNotExist:
    return HttpResponseServerError('We could not find your registration')

  try:
    attendee.checked_in = True
    attendee.save()
  except:
    return HttpResponseServerError('We encountered a problem with your checkin')

  return scale_render_to_response(request, 'reg6/reg_finish_checkin.html',
    {'title': 'Checked In',
     'attendee': attendee,
    })

def RedeemCoupon(request):
  PAYMENT_STEP = 7

  if request.method != 'POST':
    return HttpResponseRedirect('/utoscreg/')
  if 'HTTP_REFERER' not in request.META  or \
    '/utoscreg/payment/' not in request.META['HTTP_REFERER']:
    return HttpResponseRedirect('/utoscreg/')

  required_vars = [
    'code',
    'order',
  ]

  r = CheckVars(request, required_vars, [])
  if r:
    return r

  try:
    coupon = models.Coupon.objects.get(code=request.POST['code'])
  except models.Coupon.DoesNotExist:
    return scale_render_to_response(request, 'reg6/reg_error.html',
      {'title': 'Registration Problem',
       'error_message': 'Invalid coupon'
      })

  if not coupon.is_valid():
    return scale_render_to_response(request, 'reg6/reg_error.html',
      {'title': 'Registration Problem',
       'error_message': 'This coupon has expired'
      })

  try:
    temp_order = models.TempOrder.objects.get(order_num=request.POST['order'])
  except models.TempOrder.DoesNotExist:
    return scale_render_to_response(request, 'reg6/reg_error.html',
      {'title': 'Registration Problem',
       'error_message': 'cannot get temp order'
      })

  num_attendees = len(temp_order.attendees_list())
  if num_attendees > coupon.max_attendees:
    return scale_render_to_response(request, 'reg6/reg_error.html',
      {'title': 'Registration Problem',
       'error_message': 'coupon not valid for the number of attendees'
      })

  all_attendees_data = []
  for id in temp_order.attendees_list():
    try:
      attendee = models.Attendee.objects.get(id=id)
      if not attendee.valid:
        all_attendees_data.append(attendee)
    except models.Attendee.DoesNotExist:
      return HttpResponseServerError('cannot find an attendee')

  for person in all_attendees_data:
    # remove non-free addon items
    for item in person.ordered_items.all():
      if item.price > 0:
        person.ordered_items.remove(item)
    person.valid = True
    person.order = coupon.order
    person.badge_type = coupon.badge_type
    person.promo = None
    person.save()

  coupon.max_attendees = coupon.max_attendees - num_attendees
  if coupon.max_attendees == 0:
    coupon.used = True
  coupon.save()

  return scale_render_to_response(request, 'reg6/reg_receipt.html',
    {'title': 'Registration Payment Receipt',
     'attendees': all_attendees_data,
     'code': request.POST['code'],
     'step': PAYMENT_STEP,
     'steps_total': STEPS_TOTAL,
    })


@login_required
def AddCoupon(request):
  can_access = False
  if request.user.is_superuser:
    can_access = True
  else:
    perms = request.user.get_all_permissions()
    if 'reg6.add_order' in perms and 'reg6.add_coupon' in perms:
      can_access = True

  if not can_access:
    return HttpResponseRedirect('/accounts/profile/')

  ticket_types = {
    'expo': 'invitee',
    'full': 'invitee',
    'press': 'press',
    'speaker': 'speaker',
    'exhibitor': 'exhibitor',
    'friday': 'invitee',
  }

  if request.method == 'GET':
    tickets = []
    for ticket_type in ticket_types.keys():
      temp_tickets = models.Ticket.objects.filter(type=ticket_type)
      for t in temp_tickets:
        tickets.append(t)
    return scale_render_to_response(request, 'reg6/add_coupon.html',
      {'title': 'Add Coupon',
       'tickets': tickets,
      })

  required_vars = [
    'NAME',
    'ADDRESS',
    'CITY',
    'STATE',
    'ZIP',
    'EMAIL',
    'COUNTRY',
    'PHONE',
    'TICKET',
    'MAX_ATTENDEES',
  ]

  r = CheckVars(request, required_vars, [])
  if r:
    return HttpResponseServerError('required vars missing')

  try:
    ticket = models.Ticket.objects.get(name=request.POST['TICKET'])
  except:
    return HttpResponseServerError('cannot find ticket %s' % request.POST['TICKET'])

  bad_order_nums = [ x.order_num for x in models.Order.objects.all() ]
  order = models.Order(order_num=GenerateOrderID(bad_order_nums),
    valid=False,
    name=request.POST['NAME'],
    address=request.POST['ADDRESS'],
    city=request.POST['CITY'],
    state=request.POST['STATE'],
    zip=request.POST['ZIP'],
    country=request.POST['COUNTRY'],
    email=request.POST['EMAIL'],
    phone=request.POST['PHONE'],
    amount='0',
    payment_type=ticket_types[ticket.type],
  )

  try:
    order.save()
  except: # FIXME catch the specific db exceptions
    return HttpResponseServerError('error saving the order')

  try:
    invalid = order.validate()
  except:
    invalid = True
  if invalid:
    order.delete()
    return HttpResponseServerError('parts of the form is not filled out, please try again')

  coupon = models.Coupon(code=order.order_num,
    badge_type = ticket,
    order = order,
    used = False,
    max_attendees = request.POST['MAX_ATTENDEES'],
  )
  try:
    coupon.save()
  except: # FIXME catch the specific db exceptions
    order.delete()
    return HttpResponseServerError('error saving the coupon')

  try:
    order.valid = True
    order.save()
  except: # FIXME catch the specific db exceptions
    order.delete()
    coupon.delete()
    return HttpResponseServerError('error saving the order')

  return HttpResponse('Success! Your coupon code is: %s' % order.order_num)


@login_required
def CheckedIn(request):
  if not request.user.is_superuser:
    return HttpResponse('')
  attendees = models.Attendee.objects.filter(valid=True)
  if request.method == 'GET':
    attendees = attendees.filter(checked_in=True)
  return HttpResponse('\n'.join([PrintAttendee(f) for f in attendees]),
          mimetype='text/plain')

@login_required
def MassAdd(request):
  if not request.user.is_superuser:
    return HttpResponse('')
  if request.method == 'GET':
    response = HttpResponse()
    response.write('<html><head></head><body><form method="post">')
    response.write('<textarea name="data" rows="25" cols="80"></textarea>')
    response.write('<br /><input type="submit" /></form>')
    response.write('</body></html>')
    return response

  if 'data' not in request.POST:
    return HttpResponse('No Data')

  response = HttpResponse()
  response.write('<html><head></head><body>')

  data = request.POST['data'].split('\n')
  for entry in data:
    entry = entry.strip()
    if not entry:
      continue
    entry_split = entry.split(',')
    if len(entry_split) != 7:
      response.write('bad data: %s<br />\n' % entry)
      continue

    try:
      order = models.Order.objects.get(order_num=entry_split[5])
    except models.Order.DoesNotExist:
      response.write('bad order number: %s<br />\n' % entry_split[5])
      continue

    try:
      ticket = models.Ticket.objects.get(name=entry_split[6])
    except models.Ticket.DoesNotExist:
      response.write('bad ticket type: %s<br />\n' % entry_split[6])
      continue

    attendee = models.Attendee()
    attendee.first_name = entry_split[0]
    attendee.last_name = entry_split[1]
    attendee.org = entry_split[2]
    attendee.zip = entry_split[3]
    attendee.email = entry_split[4]
    attendee.valid = True
    attendee.checked_in = False
    attendee.can_email = True
    attendee.order = order
    attendee.badge_type = ticket
    invalid = attendee.validate()
    if invalid:
      response.write('bad entry: %s<br />\n' % attendee.validate())
      continue
    attendee.save()
    response.write('Added %s<br />\n' % entry)

  response.write('</body></html>')
  return response

@login_required
def ClearBadOrder(request):
  if not request.user.is_superuser:
    return HttpResponse('')

  try:
    order = models.Order.objects.get(order_num='')
    order.delete()
  except models.Order.DoesNotExist:
    return HttpResponse('Not Found')

  return HttpResponse('Done')

# vim:softtabstop=2:shiftwidth=2
