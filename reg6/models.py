import datetime
import decimal

from django.db import models
from scale.reg6 import validators

# Create your models here.

SALUTATION_CHOICES = (
  ('Mr', 'Mr.'),
  ('Ms', 'Ms.'),
  ('Mrs', 'Mrs.'),
  ('Dr', 'Dr.'),
)

PAYMENT_CHOICES = (
  ('verisign', 'Verisign'),
  ('google', 'Google Checkout'),
  ('cash', 'Cash'),
  ('invitee', 'Invitee'),
  ('exhibitor', 'Exhibitor'),
  ('speaker', 'Speaker'),
  ('press', 'Press'),
  ('paypal', 'PayPal'),
)

TICKET_CHOICES = (
  ('expo', 'Expo Only'),
  ('full', 'Full'),
  ('press', 'Press'),
  ('speaker', 'Speaker'),
  ('exhibitor', 'Exhibitor'),
  ('staff', 'Staff'),
  ('thursday', 'Thursday Only'),
)

class Order(models.Model):
  # basic info
  order_num = models.CharField(maxlength=10, primary_key=True,
    validator_list = [validators.isValidOrderNumber],
    help_text='Unique 10 upper-case letters + numbers code')
  valid = models.BooleanField()
  date = models.DateTimeField(default=datetime.datetime.now)

  # name and address
  name = models.CharField(maxlength=120)
  address = models.CharField(maxlength=120)
  city = models.CharField(maxlength=60)
  state = models.CharField(maxlength=60)
  zip = models.CharField(maxlength=20)
  country = models.CharField(maxlength=60, blank=True)

  # contact info
  email = models.EmailField()
  phone = models.CharField(maxlength=20, blank=True)

  # payment info
  amount = models.FloatField(max_digits=5, decimal_places=2,
    validator_list = [validators.isNotNegative])
  payment_type = models.CharField(maxlength=10, choices=PAYMENT_CHOICES)
  auth_code = models.CharField(maxlength=30, blank=True,
    help_text='Only used by Verisign and PayPal (txn_id)')
  resp_msg = models.CharField(maxlength=60, blank=True,
    help_text='Only used by Verisign')
  result = models.CharField(maxlength=60, blank=True,
    help_text='Only used by Verisign')

  class Admin:
    fields = (
      ('Billing Info', {'fields': ('name', 'address', 'city', 'state', 'zip', 'country')}),
      ('Contact Info', {'fields': ('email', 'phone')}),
      ('Order Info', {'fields': ('order_num', 'valid')}),
      ('Payment Info', {'fields': ('amount', 'payment_type', 'auth_code', 'resp_msg', 'result')}),
    )
    list_display = ('order_num', 'date', 'name', 'address', 'city', 'state', 'zip', 'country', 'email', 'phone', 'amount', 'payment_type', 'valid')
    list_filter = ('date', 'payment_type', 'valid')
    save_on_top = True

  class Meta:
    permissions = (('view_order', 'Can view order'),)

  def __str__(self):
    return "%s" % self.order_num


class TicketManager(models.Manager):
  def get_query_set(self):
    exclude = []
    set = super(TicketManager, self).get_query_set()
    for item in set:
      if not item.is_public():
        exclude.append(item)
    for item in exclude:
      set = set.exclude(name=item.name)
    return set

  def names(self):
    name_list = []
    for f in self.get_query_set():
      name_list.append(f.name)
    return name_list


class Ticket(models.Model):
  name = models.CharField(maxlength=5, primary_key=True,
    validator_list = [validators.isAllCapsDigits],
    help_text='Up to 5 letters, upper-case letters + numbers')
  description = models.CharField(maxlength=60)
  type = models.CharField(maxlength=10, choices=TICKET_CHOICES)
  price = models.FloatField(max_digits=5, decimal_places=2,
    validator_list = [validators.isNotNegative])
  public = models.BooleanField(help_text='Publicly available on the order page')
  start_date = models.DateField(null=True, blank=True,
    validator_list = [validators.isValidStartStopDates],
    help_text='Available on this day')
  end_date = models.DateField(null=True, blank=True,
    help_text='Not Usable on this day')

  objects = models.Manager()
  public_objects = TicketManager()

  def is_public(self):
    if not self.public:
      return False
    today = datetime.date.today()
    if self.start_date and self.start_date > today:
      return False
    if self.end_date and self.end_date <= today:
      return False
    return True

  class Admin:
    list_display = ('name', 'description', 'type', 'price', 'public',
      'start_date', 'end_date')
    list_filter = ('type', 'public', 'start_date', 'end_date')
    save_on_top = True

  class Meta:
    permissions = (('view_ticket', 'Can view ticket'),)

  def __str__(self):
    return "%s" % self.name


class PromoCodeManager(models.Manager):
  def get_query_set(self):
    exclude = []
    set = super(PromoCodeManager, self).get_query_set()
    for item in set:
      if not item.is_active():
        exclude.append(item)
    for item in exclude:
      set = set.exclude(name=item.name)
    return set

  def names(self):
    name_list = []
    for f in self.get_query_set():
      name_list.append(f.name)
    return name_list

class PromoCode(models.Model):
  name = models.CharField(maxlength=5, primary_key=True,
    validator_list = [validators.isAllCapsDigits],
    help_text='Up to 5 letters, upper-case letters + numbers')
  description = models.CharField(maxlength=60)

  price_modifier = models.FloatField(max_digits=3, decimal_places=2,
    validator_list = [validators.isPositive],
    help_text='This is the price multiplier, i.e. for 0.4, $10 becomes $4.')
  active = models.BooleanField()
  start_date = models.DateField(null=True, blank=True,
    validator_list = [validators.isValidStartStopDates],
    help_text='Available on this day')
  end_date = models.DateField(null=True, blank=True,
    help_text='Not Usable on this day')
  applies_to = models.ManyToManyField(Ticket, blank=True, null=True)
  applies_to_all = models.BooleanField(help_text='Applies to all tickets')

  objects = models.Manager()
  active_objects = PromoCodeManager()

  def is_active(self):
    if not self.active:
      return False
    today = datetime.date.today()
    if self.start_date and self.start_date > today:
      return False
    if self.end_date and self.end_date <= today:
      return False
    return True

  def is_applicable_to(self, ticket):
    if self.applies_to_all:
      return True
    return ticket in self.applies_to.all()

  class Admin:
    list_display = ('name', 'description', 'price_modifier', 'active', 'start_date', 'end_date')
    list_filter = ('active', 'start_date', 'end_date')
    save_on_top = True

  class Meta:
    permissions = (('view_promocode', 'Can view promo code'),)

  def __str__(self):
    return self.name


class Item(models.Model):
  name = models.CharField(maxlength=4,
    validator_list = [validators.isAllCapsDigits],
    help_text='Unique, up to 4 upper-case letters / numbers')
  description = models.CharField(maxlength=60)
  more_info = models.TextField(maxlength=555, blank=True,null=True,
      help_text='Please use no more than 2 short paragraphs of text')

  price = models.FloatField(max_digits=5, decimal_places=2,
    validator_list = [validators.isNotNegative])

  active = models.BooleanField()
  pickup = models.BooleanField(help_text='Can we track if this item gets picked up?')
  promo = models.BooleanField(help_text='Price affected by promo code?')
  applies_to = models.ManyToManyField(Ticket, blank=True, null=True)
  applies_to_all = models.BooleanField(help_text='Applies to all tickets')

  class Admin:
    list_display = ('name', 'description', 'price', 'active', 'pickup', 'promo')
    list_filter = ('active', 'pickup', 'promo')
    save_on_top = True

  class Meta:
    permissions = (('view_item', 'Can view item'),)

  def __str__(self):
    return '%s (%s)' % (self.description, self.name)


class Answer(models.Model):
  question = models.ForeignKey("Question", edit_inline=models.TABULAR,
    num_in_admin=10)
  text = models.CharField(maxlength=200, core=True)

  class Admin:
    list_display = ('question', '__str_text__')
    save_on_top = True

  class Meta:
    permissions = (('view_answer', 'Can view answer'),)

  def __str_text__(self):
    if len(self.text) > 37:
      return '%s...' % self.text[:37]
    return '%s' % self.text

  def __str__(self):
    return '(%d) %s' % (self.question.id, self.__str_text__())


class Question(models.Model):
  text = models.CharField(maxlength=200)
  active = models.BooleanField()
  applies_to_tickets = models.ManyToManyField(Ticket, blank=True, null=True)
  applies_to_items = models.ManyToManyField(Item, blank=True, null=True)
  applies_to_all = models.BooleanField(help_text='Applies to all tickets')

  class Admin:
    save_on_top = True

  class Meta:
    permissions = (('view_question', 'Can view question'),)

  def get_answers(self):
    return Answer.objects.filter(question=self.id)

  def __str__(self):
    if len(self.text) > 37:
      return '%s...' % self.text[:37]
    return '%s' % self.text


class Attendee(models.Model):
  # badge info
  badge_type = models.ForeignKey(Ticket)
  order = models.ForeignKey(Order, blank=True, null=True)
  valid = models.BooleanField()
  checked_in = models.BooleanField(help_text='Only for valid attendees',
    validator_list = [validators.isValidAttendeeCheckin])

  # attendee name
  salutation = models.CharField(maxlength=10, choices=SALUTATION_CHOICES, blank=True)
  first_name = models.CharField(maxlength=60)
  last_name = models.CharField(maxlength=60)
  title = models.CharField(maxlength=60, blank=True)
  org = models.CharField(maxlength=60, blank=True)

  # contact info
  email = models.EmailField()
  zip = models.CharField(maxlength=20)
  phone = models.CharField(maxlength=20, blank=True)

  # etc
  promo = models.ForeignKey(PromoCode, blank=True, null=True)
  ordered_items = models.ManyToManyField(Item, blank=True, null=True)
  obtained_items = models.CharField(maxlength=60, blank=True,
    validator_list = [validators.isValidObtainedItems],
    help_text='comma separated list of items')
  can_email = models.BooleanField()
  answers = models.ManyToManyField(Answer, blank=True, null=True,
    validator_list = [validators.isQuestionsUnique])

  def ticket_cost(self):
    price_modifier = 1
    if self.promo:
      price_modifier = self.promo.price_modifier
      if (self.promo.applies_to_all or
          self.badge_type in self.promo.applies_to.all()):
        price_modifier = self.promo.price_modifier

    total = self.badge_type.price * price_modifier
    for item in self.ordered_items.all():
      additional_cost = item.price
      if item.promo:
        additional_cost *= price_modifier
      total += additional_cost
    return total

  class Admin:
    fields = (
      ('Attendee Info', {'fields': ('salutation', 'first_name', 'last_name', 'title', 'org')}),
      ('Contact Info', {'fields': ('email', 'zip', 'phone')}),
      ('Badge Info', {'fields': ('badge_type', 'valid', 'checked_in')}),
      ('Items', {'fields': ('ordered_items', 'obtained_items')}),
      ('Misc', {'fields': ('promo', 'order', 'answers')}),
    )
    list_display = ('id', 'first_name', 'last_name', 'email', 'zip', 'badge_type', 'valid', 'checked_in', 'order', 'promo')
    list_filter = ('badge_type', 'valid', 'checked_in', 'promo')
    save_on_top = True

  class Meta:
    permissions = (('view_attendee', 'Can view attendee'),)

  def __str__(self):
    return "%s (%s) " % (self.id, self.email)

class TempOrder(models.Model):
  TWOPLACES = decimal.Decimal(10) ** -2

  order_num = models.CharField(maxlength=10, primary_key=True,
    validator_list = [validators.isValidOrderNumber],
    help_text='Unique 10 upper-case letters + numbers code')
  attendees = models.TextField(
    validator_list = [validators.isCommaSeparatedInts])
  date = models.DateTimeField(auto_now_add=True)

  def attendees_list(self):
    y = list()
    if self.attendees.find(',') != -1:
      for x in self.attendees.split(','):
        y.append(x)
    else:
      y.append(self.attendees)

    return y

  def total(self):
    """Grab the total amount due for this order."""
    total = sum(
        [i.ticket_cost()
          for i in Attendee.objects.filter(id__in=self.attendees_list())]
    )
    return decimal.Decimal(str(total)).quantize(self.TWOPLACES)

  def __str__(self):
    return "%s" % self.order_num

  class Admin:
    pass

class Coupon(models.Model):
  code = models.CharField(maxlength=10, primary_key=True,
    validator_list = [validators.isValidOrderNumber],
    help_text='Unique 10 upper-case letters + numbers code')
  badge_type = models.ForeignKey(Ticket)
  order = models.ForeignKey(Order)
  used = models.BooleanField()
  max_attendees = models.PositiveIntegerField(maxlength=3)
  expiration = models.DateField(null=True, blank=True,
    help_text='Not usable on this day')

  def is_valid(self):
    if self.used:
      return False
    if self.expiration and self.expiration <= datetime.date.today():
      return False
    return True

  class Admin:
    list_display = ('code', 'badge_type', 'order', 'used', 'max_attendees', 'expiration')
    list_filter = ('code', 'used', 'badge_type')
    save_on_top = True

  class Meta:
    permissions = (('view_coupon', 'Can view coupon'),)

# vim:softtabstop=2:shiftwidth=2
