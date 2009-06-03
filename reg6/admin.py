from django.contrib import admin
from django.contrib.sites.models import Site
from reg6.models import Coupon,Attendee,Question,Answer,Item,PromoCode,Ticket,Order

site = admin.AdminSite()

#  class Admin:
#    list_display = ('code', 'badge_type', 'order', 'used', 'max_attendees', 'expiration')
#    list_filter = ('code', 'used', 'badge_type')
#    save_on_top = True

#Order
#  class Admin:
#    fields = (
#      ('Billing Info', {'fields': ('name', 'address', 'city', 'state', 'zip', 'country')}),
#      ('Contact Info', {'fields': ('email', 'phone')}),
#      ('Order Info', {'fields': ('order_num', 'valid')}),
#      ('Payment Info', {'fields': ('amount', 'payment_type', 'auth_code', 'resp_msg', 'result')}),
#    )
#    list_display = ('order_num', 'date', 'name', 'address', 'city', 'state', 'zip', 'country', 'email', 'phone', 'amount', 'payment_type', 'valid')
#    list_filter = ('date', 'payment_type', 'valid')
#    save_on_top = True

admin.site.register(Coupon)
admin.site.register(Attendee)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(Item)
admin.site.register(PromoCode)
admin.site.register(Ticket)
admin.site.register(Order)

