"""Classes for accepting PayPal's Instant Payment Notification messages in a
Django application (or Django-on-App-Engine):

As seen on Django Snippets__.

.. __: http://www.djangosnippets.org/snippets/969/

https://www.paypal.com/ipn

Usage:

from paypal import Endpoint  # Or AppEngineEndpoint as Endpoint

class MyEndPoint(Endpoint):
    def process(self, data):
        # Do something with valid data from PayPal - e-mail it to yourself,
        # stick it in a database, generate a license key and e-mail it to the
        # user... whatever

    def process_invalid(self, data):
        # Do something with invalid data (could be from anywhere) - you 
        # should probably log this somewhere

These methods can optionally return an HttpResponse - if they dont, a 
default response will be sent.

Then in urls.py:

    (r'^endpoint/$', MyEndPoint()),

"data" looks something like this:

{
    'business': 'your-business@example.com',
    'charset': 'windows-1252',
    'cmd': '_notify-validate',
    'first_name': 'S',
    'last_name': 'Willison',
    'mc_currency': 'GBP',
    'mc_fee': '0.01',
    'mc_gross': '0.01',
    'notify_version': '2.4',
    'payer_business_name': 'Example Ltd',
    'payer_email': 'payer@example.com',
    'payer_id': '5YKXXXXXX6',
    'payer_status': 'verified',
    'payment_date': '11:45:00 Aug 13, 2008 PDT',
    'payment_fee': '',
    'payment_gross': '',
    'payment_status': 'Completed',
    'payment_type': 'instant',
    'receiver_email': 'your-email@example.com',
    'receiver_id': 'CXZXXXXXQ',
    'residence_country': 'GB',
    'txn_id': '79F58253T2487374D',
    'txn_type': 'send_money',
    'verify_sign': 'AOH.JxXLRThnyE4toeuh-.oeurch23.QyBY-O1N'
}
"""

from django.http import HttpResponse
import urllib
import httplib
import logging

logging.basicConfig(
    level = logging.DEBUG,
    format = '%(asctime)s %(levelname)s %(message)s',
    filename = '/tmp/scalereg.log',
    filemode = 'w'
)

class Endpoint:

    default_response_text = 'Nothing to see here'
    #verify_url = "https://www.paypal.com/cgi-bin/webscr"

    # For debugging:
    verify_url = "https://www.sandbox.paypal.com/cgi-bin/webscr"
    httplib.HTTPConnection.debuglevel = 1

    def do_post(self, url, args):
        return urllib.urlopen(url, urllib.urlencode(args)).read()

    def verify(self, data):
            	logging.debug("verify function")
		args = {
		    'cmd': '_notify-validate',
		}
		args.update(data)
		logging.debug("Args to PayPal:\n%s\n\n" % args)
		
		vData = self.do_post(self.verify_url, args)
		logging.debug("Data from PayPal:\n%s\n\n" % vData)
#		return self.do_post(self.verify_url, args) == 'VERIFIED'
		return vData == 'VERIFIED'
		
    def default_response(self):
        return HttpResponse(self.default_response_text)

    def __call__(self, request):
    
#        import pdb
#        pdb.set_trace()
        
        r = None
        
        if request.method == 'POST':
#            data = dict()
#            for key, value in request.POST.items():
#                logging.debug("key: %s value: %s", key, value)
#                data[key] = value
            data = dict(request.POST.items())
#            # We need to post that BACK to PayPal to confirm it
            logging.debug("Data to PayPal:\n%s\n\n" % data)
            
            if self.verify(data):
                logging.debug("if verify data")
                r = self.process(data)
            else:
                logging.debug("data invalid")
                r = self.process_invalid(data)

        if r:
            return r
        else:
            return self.default_response()


    def process(self, data):
        pass

    def process_invalid(self, data):
        pass

class AppEngineEndpoint(Endpoint):

    def do_post(self, url, args):
        from google.appengine.api import urlfetch
        return urlfetch.fetch(
            url = url,
            method = urlfetch.POST,
            payload = urllib.urlencode(args)
        ).content
