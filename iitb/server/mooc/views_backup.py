"""
Mooc Views
"""
import datetime
import json
import logging
import random
import re
import string       # pylint: disable=W0402
import urllib
import uuid
import time
from collections import defaultdict
from pytz import UTC
import mooc.signals
from django.conf import settings
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.models import User, AnonymousUser
from mooc.models import Institute_Registration, State, City, Institute_Accreditation, Accreditation, Institute_Designation, Role, Institute_Status, Student_Institute, Institute_Course, Identity, Institute_Identity
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import password_reset_confirm
# from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.context_processors import csrf
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.core.validators import validate_email, validate_slug, ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.http import (HttpResponse, HttpResponseBadRequest, HttpResponseForbidden,
                         Http404)
from django.shortcuts import redirect, render_to_response
from django_future.csrf import ensure_csrf_cookie
from django.utils.http import cookie_date, base36_to_int
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST, require_GET
from django.contrib.admin.views.decorators import staff_member_required

from ratelimitbackend.exceptions import RateLimitException

from edxmako.shortcuts import render_to_response, render_to_string

from course_modes.models import CourseMode
from student.models import (
    Registration, UserProfile, PendingNameChange,
    PendingEmailChange, CourseEnrollment, unique_id_for_user,
    CourseEnrollmentAllowed, UserStanding, LoginFailures
)
from mooc.models import Person, Institute_Registration, Central_Coordinator

from student.forms import PasswordResetFormNoActive

from verify_student.models import SoftwareSecurePhotoVerification, MidcourseReverificationWindow
from certificates.models import CertificateStatuses, certificate_status_for_student

from xmodule.course_module import CourseDescriptor
from xmodule.modulestore.exceptions import ItemNotFoundError
from xmodule.modulestore.django import modulestore
from xmodule.modulestore import MONGO_MODULESTORE_TYPE

from collections import namedtuple

from courseware.courses import get_courses, sort_by_announcement
from courseware.access import has_access

from external_auth.models import ExternalAuthMap
import external_auth.views

from bulk_email.models import Optout, CourseAuthorization
import shoppingcart

import track.views

from dogapi import dog_stats_api
from pytz import UTC

from util.json_request import JsonResponse

from microsite_configuration.middleware import MicrositeConfiguration

from util.password_policy_validators import (
    validate_password_length, validate_password_complexity,
    validate_password_dictionary
)

from django.core.management import call_command
from django.db.models import Q
import commands
from student.models import *
from mooc.models import *
import ast
import hashlib

log = logging.getLogger("edx.student")
AUDIT_LOG = logging.getLogger("audit")

Article = namedtuple('Article', 'title url author image deck publication publish_date')
ReverifyInfo = namedtuple('ReverifyInfo', 'course_id course_name course_number date status display')  # pylint: disable=C0103

def csrf_token(context):
    """A csrf token that can be included in a form."""
    csrf_token = context.get('csrf_token', '')
    if csrf_token == 'NOTPROVIDED':
        return ''
    return (u'<div style="display:none"><input type="hidden"'
            ' name="csrfmiddlewaretoken" value="%s" /></div>' % (csrf_token))

class AccountValidationError(Exception):
    def __init__(self, message, field):
        super(AccountValidationError, self).__init__(message)
        self.field = field


def nav_institute_register(request, extra_context=None):
    """
    This view will display the institute registration form
    """
    #if request.user.is_authenticated():
    #   return redirect(reverse('dashboard'))
    #if settings.FEATURES.get('AUTH_USE_MIT_CERTIFICATES_IMMEDIATE_SIGNUP'):
        # Redirect to branding to process their certificate if SSL is enabled
        # and registration is disabled.
    #    return redirect(reverse('root'))

    context = {
        'course_id': request.GET.get('course_id'),
        'enrollment_action': request.GET.get('enrollment_action'),
        'platform_name': MicrositeConfiguration.get_microsite_configuration_value(
            'platform_name',
            settings.PLATFORM_NAME
        ),
    }
    if extra_context is not None:
        context.update(extra_context)

    #if context.get("extauth_domain", '').startswith(external_auth.views.SHIBBOLETH_DOMAIN_PREFIX):
    #      return render_to_response('register-shib.html', context)
    return render_to_response('institute_register.html', context)

def GenerateUsername(email):

    

    try:
        User.objects.get(username=email)
	email += str(random.randint(0,1000))
        return GenerateUsername(email)
    except User.DoesNotExist:
        return email;

@ensure_csrf_cookie
def institute_register_redirect(request):
    """
    """
    return render_to_response("institute_register_redirect.html")

@ensure_csrf_cookie
def register_institute(request, post_override=None):

    """
    JSON call to create new institute.
    """
    js = {'success': False}
    post_vars = post_override if post_override else request.POST
    extra_fields = getattr(settings, 'REGISTRATION_EXTRA_FIELDS', {})

    
    for a in ['name', 'state', 'city']:
        if a not in post_vars:
            js['value'] = _("Error (401 {field}). E-mail us.").format(field=a)
            js['field'] = a
            return JsonResponse(js, status=400)


    required_post_vars = ['name', 'state', 'city', 'pincode', 'address', 'website', 'headName', 'headEmail', 'headMobile', 'rccName', 'rccEmail', 'rccMobile', 'studentIdentity']


    for field_name in required_post_vars:
        if field_name in ('state', 'city'):
           min_length = 1
        else:
           min_length = 2

        if len(post_vars[field_name]) < min_length:
            error_str = {
                'name': _('Name must be minimum of two characters long'),
                'state': _('A state is required'),
                'address': _('Your address is required'),
                'city': _('A city is required'),
		        'pincode' : _('Your Pincode is required'),
                'website' : _('Your website is required'),
                'headName' : _('Head Name must be minimum of two characters long'),
                'headEmail' : _('A properly formatted e-mail is required'),
                'headMobile' : _('Head Mobile must be of 10 digits'),
                'rccName' : _('RCC Name must be minimum of two characters long'),
                'rccEmail' : _('A properly formatted e-mail is required'),
                'rccMobile' : _('RCC Mobile must be of 10 digits'),
                'honor_code': _('Agreeing to the Honor Code is required'),
                'terms_of_service': _('Accepting Terms of Service is required')
            }
            js['value'] = error_str[field_name]
            js['field'] = field_name
            return JsonResponse(js, status=400)
    try:
        validate_email(post_vars['headEmail'])
    except ValidationError:
        js['value'] = _("Valid e-mail is required.").format(field=a)
        js['field'] = 'email'
        return JsonResponse(js, status=400)

    try:
        validate_email(post_vars['rccEmail'])
    except ValidationError:
        js['value'] = _("Valid e-mail is required.").format(field=a)
        js['field'] = 'email'
        return JsonResponse(js, status=400)



    if extra_fields.get('honor_code', 'required') == 'required' and \
            post_vars.get('honor_code', 'false') != u'true':
        js['value'] = _("To enroll, you must follow the honor code.").format(field=a)
        js['field'] = 'honor_code'
        return JsonResponse(js, status=400)


    if extra_fields.get('terms_of_service', 'required') == 'required' and \
            post_vars.get('terms_of_service', 'false') != u'true':
        js['value'] = _("To enroll, you must accept terms of service.").format(field=a)
        js['field'] = 'terms_of_service'
        return JsonResponse(js, status=400)

    
    status=Institute_Status.objects.filter(name="Pending")[0].id 

    institute = Institute_Registration( name=post_vars['name'], state_id=post_vars['state'], city_id=post_vars['city'], pincode=post_vars['pincode'], status_id=status, is_parent=False, address=post_vars['address'], website=post_vars['website'])


    if post_vars['headEmail'] == post_vars['rccEmail']:
            js['value'] = _("Please provide different emails for Head and Coordinator").format(email=post_vars['headEmail'])
            js['field'] = 'email'
            return JsonResponse(js,status=400)


    if len(User.objects.filter(email=str(post_vars['headEmail']))) > 0:
            js = {'success': False}
            js['value'] = _("An account with the Email '{email}' already exists.").format(email=post_vars['headEmail'])
            js['field'] = 'email'
            return JsonResponse(js,status=400)

    if len(User.objects.filter(email=str(post_vars['rccEmail']))) > 0:
            js = {'success': False}
            js['value'] = _("An account with the Email '{email}' already exists.").format(email=post_vars['rccEmail'])
            js['field'] = 'email'
            return JsonResponse(js,status=400)


    try:
        institute.save()
    except IntegrityError as e:
        js = {'success': False}
        
        if len(Institute_Registration.objects.filter(name=post_vars['name'])) > 0:
            js['value'] = _("An Institute with the name '{name}' already exists.").format(name=post_vars['name'])
            js['field'] = 'name'
            return JsonResponse(js,status=400)
        
	
    insti_id= institute.id

    accreditation = request.POST.getlist('accreditation')

    for index in accreditation:
    	acc = Institute_Accreditation(accreditation_id=index , institute_id=insti_id)
    	acc.save()


    headUsername = post_vars['headEmail'].split('@')
    headUsername = GenerateUsername(headUsername[0])

    headPass = uuid.uuid4().hex[0:10]
    
    user = User(username=headUsername,
                email=post_vars['headEmail'],
                is_active=False)
    user.set_password(headPass)
   
    try:
        user.save()
        head_user_object = user
    except IntegrityError as e:
        js = {'success': False}
        # Figure out the cause of the integrity error
        if len(User.objects.filter(email=post_vars['headEmail'])) > 0:
            js['value'] = _("An account with the Email '{email}' already exists.").format(email=post_vars['headEmail'])
            js['field'] = 'email'
            return JsonResponse(js,status=400)

    profile = UserProfile(user=user)
    profile.name = post_vars['headName']
    profile.year_of_birth = None
    person = Person(user=user)
   
    person.mobile = post_vars.get('headMobile')
    person.save()
       
    try:
        profile.save()
    except Exception:
        log.exception("UserProfile creation failed for user {id}.".format(id=user.id))


    head_role_id = Role.objects.filter(name="Institute Head")[0].id


    designation = Institute_Designation(user=user, institute_id=insti_id, role_id=head_role_id, is_approved=False)
    designation.save()




    rccUsername = post_vars['rccEmail'].split('@')
    rccUsername = GenerateUsername(rccUsername[0])

    rccPass = uuid.uuid4().hex[0:10]
    
    user = User(username=rccUsername,
                email=post_vars['rccEmail'],
                is_active=False)
    user.set_password(rccPass)


 
   
   
    try:
        user.save()
        rcc_user_object = user
    except IntegrityError as e:
        js = {'success': False}
        # Figure out the cause of the integrity error
        if len(User.objects.filter(email=post_vars['rccEmail'])) > 0:
            js['value'] = _("An account with the Email '{email}' already exists.").format(email=post_vars['rccEmail'])
            js['field'] = 'email'
            return JsonResponse(js,status=400)

    profile = UserProfile(user=user)
    profile.name = post_vars['rccName']
    profile.year_of_birth = None
    person = Person(user=user)
   
    person.mobile = post_vars.get('rccMobile')
    person.save()
       
    try:
        profile.save()
    except Exception:
        log.exception("UserProfile creation failed for user {id}.".format(id=user.id))


    ic_role_id = Role.objects.filter(name="Institute Coordinator")[0].id
    designation = Institute_Designation(user=user, institute_id=insti_id, role_id=ic_role_id, is_approved=False)
    designation.save()

#identity_name = post_vars.get('studentIdentity')
 #   student_identity = Identity(name=identity_name)
  #  student_identity.save()
    
   # institute_id = Institute_Registration.objects.filter(name=post_vars.get('name'))[0].id
    #identity_id = Identity.objects.filter(name=identity_name)[0].id
    #institute_identity = Institute_Identity(institute_id=institute_id, identity_id=identity_id)
    #institute_identity.save() '''
    

    context = {'name': "test",}

    # composes thank you email
    subject = render_to_string('emails/thankyou_email_subject.txt',context)
    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())
    message = render_to_string('emails/thankyou_email_body.txt',context)

    # don't send email if we are doing load testing or random user generation for some reason
    if not (settings.FEATURES.get('AUTOMATIC_AUTH_FOR_TESTING')):
        from_address = MicrositeConfiguration.get_microsite_configuration_value(
            'email_from_address',
            settings.DEFAULT_FROM_EMAIL
        )
        try:
            if settings.FEATURES.get('REROUTE_ACTIVATION_EMAIL'):
                dest_addr = settings.FEATURES['REROUTE_ACTIVATION_EMAIL']
                message = ("Thank you for mail %s (%s):\n" % (head_user_object, head_user_object.email) +
                           '-' * 80 + '\n\n' + message)
                send_mail(subject, message, from_address, [dest_addr], fail_silently=False)
            else:
                _res = head_user_object.email_user(subject, message, from_address)
                _res1 = rcc_user_object.email_user(subject, message, from_address)
                
        except:
            log.warning('Unable to send thank you email to user', exc_info=True)
            js['value'] = _('Could not send thank you e-mail.')
            # What is the correct status code to use here? I think it's 500, because
            # the problem is on the server's end -- but also, the account was created.
            # Seems like the core part of the request was successful.
            return JsonResponse(js, status=500)     

    return JsonResponse({'success': True,})



@login_required
def token(request):
    '''
    Return a token for the backend of annotations.
    It uses the course id to retrieve a variable that contains the secret
    token found in inheritance.py. It also contains information of when
    the token was issued. This will be stored with the user along with
    the id for identification purposes in the backend.
    '''
    course_id = request.GET.get("course_id")
    course = course_from_id(course_id)
    dtnow = datetime.datetime.now()
    dtutcnow = datetime.datetime.utcnow()
    delta = dtnow - dtutcnow
    newhour, newmin = divmod((delta.days * 24 * 60 * 60 + delta.seconds + 30) // 60, 60)
    newtime = "%s%+02d:%02d" % (dtnow.isoformat(), newhour, newmin)
    secret = course.annotation_token_secret
    custom_data = {"issuedAt": newtime, "consumerKey": secret, "userId": request.user.email, "ttl": 86400}
    newtoken = create_token(secret, custom_data)
    response = HttpResponse(newtoken, mimetype="text/plain")
    return response

@ensure_csrf_cookie
def member_institutions(request):
    """
    This view displays the data of IITBombayX members
    """
        
    data = Institute_Registration.objects.all()
    context={'member_institutions':data,
                }
    

    return render_to_response('iitbombayx-members.html', context)

@ensure_csrf_cookie
def how_it_works(request):
    
    return render_to_response('how-it-works.html')


@login_required
@ensure_csrf_cookie
def cc_institute_details(request,post_override=None):
    """
    This view will display the institute registration form
    """
    user = request.user
    try:
        if user.is_superuser :
           rolename="Admin"
        else: 
           Central_Coordinator.objects.filter(user=user,is_approved=True)[0]    	            
           rolename="Central Coordinator"
    except:
        if len(user.groups.all()) > 0:
            rolename = "Central Course Assistant"
        else:
            try:
                role=Institute_Designation.objects.filter(user=user)	
                role_names=Role.objects.filter(name=role[0].role)
                rolename=str(role_names[0])
            except:
                rolename="Student"

    if not rolename == "Central Coordinator":
        return render_to_response('static_templates/404.html')

    institute_object = Institute_Registration.objects.all()


    context={'institute_object':institute_object,
             'rolename': rolename,
                }
    
    return render_to_response('institute_details.html', context)

@login_required   
def course_list(request):
    """
    This view will display the course list of institute coordinator
    """
   
    return render_to_response('ic_course_list.html')

@login_required
@ensure_csrf_cookie
def approve_students(request):
    """
    This view will allow institute coordinator to approve the students
    """

    user = request.user
    try:
        if user.is_superuser :
           rolename="Admin"
        else: 
           Central_Coordinator.objects.filter(user=user,is_approved=True)[0]    	            
           rolename="Central Coordinator"
    except:
        if len(user.groups.all()) > 0:
            rolename = "Central Course Assistant"
        else:
            try:
                role=Institute_Designation.objects.filter(user=user)
                institute = int( role[0].institute.id)	
                role_names=Role.objects.filter(name=role[0].role)
                rolename=str(role_names[0])
            except:
                rolename="Student"
    try:
        Student_Institute_Objects = Student_Institute.objects.filter(institute_id=institute)
        
        context = { 'Student_Institute_Objects' : Student_Institute_Objects,
                    'rolename': rolename,
                    }
        return render_to_response('ic_approve_students.html',context)
    except:
        return render_to_response('static_templates/404.html')

@login_required
@ensure_csrf_cookie
def enrolled_courses(request):
    """
    This view will display the courses enrolled by institute coordinator 
    """
    user = request.user
    try:
        if user.is_superuser :
           rolename="Admin"
        else: 
           Central_Coordinator.objects.filter(user=user,is_approved=True)[0]    	            
           rolename="Central Coordinator"
    except:
        if len(user.groups.all()) > 0:
            rolename = "Central Course Assistant"
        else:
            try:
                role=Institute_Designation.objects.filter(user=user)
                institute = int( role[0].institute.id)	
                role_names=Role.objects.filter(name=role[0].role)
                rolename=str(role_names[0])
            except:
                rolename="Student"
    try:

        Institute_Course_Objects = Institute_Course.objects.filter(institute_id=institute)
        context = { 'rolename': rolename, 'Institute_Course_Objects' : Institute_Course_Objects,
                    }
 
        return render_to_response('ic_enrolled_courses.html',context)
    except:
        return render_to_response('static_templates/404.html')


@login_required
@ensure_csrf_cookie
def ic_courses(request):
    """
    This view will display the students enrolled by institute coordinator
    """
    user = request.user
    try:
        if user.is_superuser :
           rolename="Admin"
        else: 
           Central_Coordinator.objects.filter(user=user,is_approved=True)[0]    	            
           rolename="Central Coordinator"
    except:
        if len(user.groups.all()) > 0:
            rolename = "Central Course Assistant"
        else:
            try:
                role=Institute_Designation.objects.filter(user=user)	
                role_names=Role.objects.filter(name=role[0].role)
                rolename=str(role_names[0])
            except:
                rolename="Student"
    context = { 'rolename': rolename,
                }   
    return render_to_response('courseware/courses.html',context)

@login_required
@ensure_csrf_cookie
def enrolled_students(request):
    """
    This view will display the students enrolled by institute coordinator
    """
    user = request.user
    try:
        if user.is_superuser :
           rolename="Admin"
        else: 
           Central_Coordinator.objects.filter(user=user,is_approved=True)[0]    	            
           rolename="Central Coordinator"
    except:
        if len(user.groups.all()) > 0:
            rolename = "Central Course Assistant"
        else:
            try:
                role=Institute_Designation.objects.filter(user=user)	
                role_names=Role.objects.filter(name=role[0].role)
                rolename=str(role_names[0])
            except:
                rolename="Student"
    context = { 'rolename': rolename,
                }   
    return render_to_response('ic_enrolled_students.html',context)

@login_required
@ensure_csrf_cookie
def ins_selection(request, post_override=None):
    """ 
    This view allows Student to select Institute in Student Dashboard 
    """
    if not request.user.is_authenticated:
        raise Http404

    user = request.user
    post_vars = post_override if post_override else request.POST
    institute_id = post_vars['ins_id']
    status=Institute_Status.objects.filter(name="Pending")[0].id

    try:    
        Student_Institute(user=user, institute_id=institute_id,status_id=status).save()    
    except:
        raise

    # composes Institute Selection Information Mail
    subject = render_to_string('emails/select_institute_subject.txt',{})
    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())
    message = render_to_string('emails/select_institute_body.txt',{})
    
    # don't send email if we are doing load testing or random user generation for some reason
    if not (settings.FEATURES.get('AUTOMATIC_AUTH_FOR_TESTING')):
        from_address = MicrositeConfiguration.get_microsite_configuration_value(
            'email_from_address',
            settings.DEFAULT_FROM_EMAIL
        )
        try:
             ic_role_id = Role.objects.filter(name="Institute Coordinator")[0].id
             Institute_Designation_object = Institute_Designation.objects.filter(institute_id=institute_id, role_id=ic_role_id)[0]
             _res = Institute_Designation_object.user.email_user(subject, message, from_address)

        except:
            log.warning('Unable to send email to institute coordinator', exc_info=True)
            js['value'] = _('Could not send e-mail.')
            # What is the correct status code to use here? I think it's 500, because
            # the problem is on the server's end -- but also, the account was created.
            # Seems like the core part of the request was successful.
            return JsonResponse(js, status=500)     

    return HttpResponse(json.dumps({'success': True}))

@login_required
def update_institute(request):
    """
    This view will allow the student to select more than one institute
    """
    status=Institute_Status.objects.filter(name="Pending")[0].id
    Student_Institute_Objects = Student_Institute.objects.filter(status_id=status)

    context = { "Student_Institute_Objects" : Student_Institute_Objects, }
    return render_to_response('update_institute.html',context)

@login_required
def student_available_courses(request):
    """
    This view will display the courses of the institute for which the student is registered
    """
   
    return render_to_response('student_available_courses.html')


def ins_approve(request, post_override=None):
    """
    This view will allow the central coordinater to approve registered institutes
    """
    if not request.user.is_authenticated:
        raise Http404

    post_vars = post_override if post_override else request.POST
    institute_id = post_vars['ins_id']
    status = post_vars['ins_status']
    initialize(institute_id)
    try:    
        Institute_object = Institute_Registration.objects.filter(id=institute_id)[0]
        status_id = int ( Institute_Status.objects.filter(name=status)[0].id )
        Institute_object.status_id = status_id
        Institute_object.save()    
    except:
        raise

    try:
        ic_role_id = Role.objects.filter(name="Institute Coordinator")[0].id    
        Institute_Designation_object = Institute_Designation.objects.filter(institute_id=institute_id, role_id=ic_role_id)[0]   
    except:
        raise
    
    try:
        Password = uuid.uuid4().hex[0:10]
        Institute_Designation_object.user.set_password(Password)
        Institute_Designation_object.user.is_active=1
        Institute_Designation_object.user.save()
    except:
        raise

    
    if status=="Approved" :
        context= { "Email" : Institute_Designation_object.user.email, "Password" : Password }
        # composes Approve Institute email
        subject = render_to_string('emails/approve_institute_email_subject.txt',context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        message = render_to_string('emails/approve_institute_email_body.txt',context)
    else :
        context= {}
        #composes Reject Institute email
        subject = render_to_string('emails/reject_institute_email_subject.txt',context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        message = render_to_string('emails/reject_institute_email_body.txt',context)


    # don't send email if we are doing load testing or random user generation for some reason
    if not (settings.FEATURES.get('AUTOMATIC_AUTH_FOR_TESTING')):
        from_address = MicrositeConfiguration.get_microsite_configuration_value(
            'email_from_address',
            settings.DEFAULT_FROM_EMAIL
        )
        try:
            _res = Institute_Designation_object.user.email_user(subject, message, from_address)

        except:
            log.warning('Unable to send Approve/Reject email to institute', exc_info=True)
            js['value'] = _('Could not send Approve/Reject e-mail.')
            # What is the correct status code to use here? I think it's 500, because
            # the problem is on the server's end -- but also, the account was created.
            # Seems like the core part of the request was successful.
            return JsonResponse(js, status=500)     

    return HttpResponse(json.dumps({'success': True}))

def fetch_ins_details(request, post_override=None):
    """
    This view will allow the central coordinater to view data of a particular institute.
    """
    if not request.user.is_authenticated:
        raise Http404


    post_vars = post_override if post_override else request.POST
    institute_id = post_vars['ins_id']

    try:
        institute_head_role_id=Role.objects.filter(name="Institute Head")[0].id
        institute_coordinator_role_id=Role.objects.filter(name="Institute Coordinator")[0].id
    except:
        raise

    insti = Institute_Registration.objects.filter(id=institute_id)[0]
    inner_list = []
    inner_list.append(insti)
    try:
        inner_list.append(Institute_Designation.objects.filter(institute_id = insti.id, role_id=institute_head_role_id)[0])
        inner_list.append(Institute_Designation.objects.filter(institute_id = insti.id, role_id=institute_coordinator_role_id)[0])
    except:
        raise

    js ={ 'success': True,
          'name':str(inner_list[0].name),
          'address': str(inner_list[0].address),
          'city': str(inner_list[0].city),
          'state': str(inner_list[0].state),
          'pincode': str(inner_list[0].pincode),
          'website': str(inner_list[0].website),
          'status': str(inner_list[0].status),
          'head_name': str(inner_list[1].user.profile.name),
          'head_email': str(inner_list[1].user.email),
          'head_contact': str(inner_list[1].user.person.mobile),
          'coordinator_name': str(inner_list[2].user.profile.name),
          'coordinator_email': str(inner_list[2].user.email),
          'coordinator_contact': str(inner_list[2].user.person.mobile)
        }

    return HttpResponse(json.dumps(js))

def student_approve(request,post_override=None):
    """
    This view will allow the Institute coordinater to approve registered students
    """
    if not request.user.is_authenticated:
        raise Http404

    post_vars = post_override if post_override else request.POST
    student_id = post_vars['student_id']
    status = post_vars['student_status']

    try:
        Student_object = Student_Institute.objects.filter(id=student_id)[0]
        status_id = int ( Institute_Status.objects.filter(name=status)[0].id )
        Student_object.status_id = status_id
        Student_object.save() 
         
    except:
        raise

    context= { }
    if status=="Approved" :
        # composes Approve Student email
        subject = render_to_string('emails/approve_student_email_subject.txt',context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        message = render_to_string('emails/approve_student_email_body.txt',context)
    else :
        #composes Reject Student email
        subject = render_to_string('emails/reject_student_email_subject.txt',context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        message = render_to_string('emails/reject_student_email_body.txt',context)


    # don't send email if we are doing load testing or random user generation for some reason
    if not (settings.FEATURES.get('AUTOMATIC_AUTH_FOR_TESTING')):
        from_address = MicrositeConfiguration.get_microsite_configuration_value(
            'email_from_address',
            settings.DEFAULT_FROM_EMAIL
        )
        try:
            _res = Student_object.user.email_user(subject, message, from_address)

        except:
            log.warning('Unable to send Approve/Reject email to user', exc_info=True)
            js['value'] = _('Could not send Approve/Reject e-mail.')
            # What is the correct status code to use here? I think it's 500, because
            # the problem is on the server's end -- but also, the account was created.
            # Seems like the core part of the request was successful.
            return JsonResponse(js, status=500)     


    return HttpResponse(json.dumps({'success': True}))

@ensure_csrf_cookie
@login_required
def ic_configuration(request):
    """
    This view will display the fields required for script download by Institute Coordinator
    """
   
    user = request.user
    try:
        if user.is_superuser :
           rolename="Admin"
        else: 
           Central_Coordinator.objects.filter(user=user,is_approved=True)[0]    	            
           rolename="Central Coordinator"
    except:
        if len(user.groups.all()) > 0:
            rolename = "Central Course Assistant"
        else:
            try:
                role=Institute_Designation.objects.filter(user=user)
                institute = int( role[0].institute.id)	
                role_names=Role.objects.filter(name=role[0].role)
                rolename=str(role_names[0])
            except:
                rolename="Student"

    context = { 'rolename': rolename,
                }
    return render_to_response('ic_configuration.html',context)

@ensure_csrf_cookie
@login_required
def download_script(request):
    """
    This view will display will redirect to download script page for Institute Coordinator
    """
   
    user = request.user
    try:
        if user.is_superuser :
           rolename="Admin"
        else: 
           Central_Coordinator.objects.filter(user=user,is_approved=True)[0]    	            
           rolename="Central Coordinator"
    except:
        if len(user.groups.all()) > 0:
            rolename = "Central Course Assistant"
        else:
            try:
                role=Institute_Designation.objects.filter(user=user)
                institute = int( role[0].institute.id)	
                role_names=Role.objects.filter(name=role[0].role)
                rolename=str(role_names[0])
            except:
                rolename="Student"

    context = { 'rolename': rolename,
                }
    return render_to_response('download-script.html',context)

@ensure_csrf_cookie
@login_required
def ic_configuration_action(request):

	platform_name=request.POST.get('platform_name')	
	site_name=request.POST.get('site_name')
	email=request.POST.get('email')

	filedetail=open("platformname.txt",'w')
	filedetail.write("Platform Name "+platform_name+"\n")
	filedetail.write("Site Name "+site_name+"\n")
	filedetail.write("Email "+Email+"\n")
	filedetail.close()


def helpsupport(request):
    """
    This view will redirect to the help and support page.
    """
    return render_to_response('helpsupport.html')



#Synchronization Code

'''
Enumerations:
'central_query_User_ins_list' as 1
'central_query_User_del_list' as 2 
'central_query_UserProfile_ins_list' as 3
'central_query_UserProfile_del_list' as 4
'central_query_Person_ins_list' as 5
'central_query_Person_del_list' as 6
'central_query_Institute_Designation_ins_list' as 7
'central_query_Institute_Designation_del_list' as 8
''' 

dict_hash = {}


#start_hash = {'Person': 'bcd8b0c2eb1fce714eab6cef0d771acc', 'Institute_Designation': 'bcd8b0c2eb1fce714eab6cef0d771acc', 'User': 'bcd8b0c2eb1fce714eab6cef0d771acc', 'UserProfile': 'bcd8b0c2eb1fce714eab6cef0d771acc'}


#Method which writes the selective data that belongs to a institute to that particular table file.
#If file doesn't exists it creates and if it exists it overwrites
#File Name are as table name + previous and are stored in respective institute directory
def write_to_file(central_prev_query_table_tuple,table_name,institute_id):
    path = str(settings.REPO_ROOT) + "/syncing/institute" + str(institute_id)
    filename = path + "/" + table_name.__name__ + "_prev"
    f = open(filename , 'w')
    f.write(str(central_prev_query_table_tuple))
    f.close()


#Method to generate the selective data that belongs to an institute.
#Input is institute_id, table_name and the values(coloumns which are required to synchronized)
def get_filtered_data(table_name,institute_id,values):
    temp = User.objects.filter(Q(student_institute__institute_id = institute_id) | Q( institute_designation__institute_id = institute_id) )
    if table_name == User:
        return temp.values_list(*values)
    else:
        temporary = table_name.objects.filter(user__id__in = temp ).values_list(*values)
        temp_str = str(temporary)
        if "datetime.date" in temp_str:
            temp_str = re.sub(r'(datetime.date\()(\d+)(, )(\d+)(, )(\d+)(\))',r'"\2-\4-\6"',temp_str)
            temporary = ast.literal_eval(temp_str)
        return temporary



#This method generates the tuples and hashes of the filtered data and stores hash into a global variable
def generate(table_name,institute_id,values):
    global dict_hash
    central_prev_query_table = get_filtered_data(table_name,institute_id,values)
    central_prev_query_table_tuple = tuple(central_prev_query_table)
    central_prev_query_table_tuple_hash = hashlib.md5(str(central_prev_query_table_tuple)).hexdigest()
    dict_hash[ table_name.__name__ ] = central_prev_query_table_tuple_hash
    print dict_hash
    return central_prev_query_table_tuple


#This method takes the institute_id and here we have mentioned the tables which we need to synchronize with the columns required and the foreign key requirements.
#Calls the generate function to generate the selective data, writes that data to file and in the end the hash of the tables are stored into a file named Hash into respective institute directory.
def initialize_part(institute_id):
    central_prev_query_table_tuple = generate(User,institute_id,['id','username','email',  'password' , 'is_active'])
    write_to_file(central_prev_query_table_tuple,User,institute_id)


    central_prev_query_table_tuple = generate(UserProfile,institute_id,['id','user_id','name','year_of_birth','gender','level_of_education','mailing_address','allow_certificate'])
    write_to_file(central_prev_query_table_tuple,UserProfile,institute_id)

    central_prev_query_table_tuple = generate(Person,institute_id,['id','user_id','birth_date','mobile'])
    write_to_file(central_prev_query_table_tuple,Person,institute_id)


    central_prev_query_table_tuple = generate(Institute_Designation,institute_id,['id','user_id','institute_id','role_id','is_approved'])
    write_to_file(central_prev_query_table_tuple,Institute_Designation,institute_id)

    hash_file_path = "syncing/institute" + str(institute_id) + "/Hash"
    f = open(hash_file_path, 'w')
    f.write(str(dict_hash))
    f.close()



#This method is to generate the directory and files required for synchronization when an institute registers
#command initialize_institute generates the directory
#initialize_part generates the files with selective data based on institute id
def initialize(institute_id):
    call_command('initialize_institute',institute_id)
    initialize_part(institute_id)



#This methods reads the data from the files related to that institute and table
def read_prev_data_from_file(table_name,institute_id):
        path = "syncing/institute" + str(institute_id)
        filename = path + "/" + table_name.__name__ + "_prev"
        f = open(filename, 'r')
        temp = f.read()
        if "datetime.date" in temp:
            temp = re.sub(r'(datetime.date\()(\d+)(, )(\d+)(, )(\d+)(\))',r'"\2-\4-\6"',temp)
        temp = ast.literal_eval(temp)
        f.close()
        return temp

#This generates the insert/update and delete list to be send to institute
def get_ins_del_list(prev_data,new_data):

    central_prev_query_list  = list( list(i) for i in prev_data )
    central_new_query_list  = list( list(i) for i in new_data )

    central_query_ins_list = [ x for x in central_new_query_list if x not in central_prev_query_list ]
    central_query_del_list = [ x for x in central_prev_query_list if x not in central_new_query_list ]

    for x in central_query_del_list:
        for y in central_query_ins_list:
            if x[0] == y[0]:
                 central_query_del_list.remove(x)

    central_query_del_list = [ [x[0]] for x in central_query_del_list ]


    return central_query_ins_list , central_query_del_list

'''
Institute sends its id ans data hashes, So we regenerate the data that we have belonging to the institute and generates their hash
Then hashes are matched , if yes data is already up to date and we update our hash file , else we filter out what data needs to be sent.
In else we matche the hashes with the hashes stored in the file, if they are matched we have current data set and the data set which institute have, in this case read data from files and find the differences.
Else we believe institute has lost the synchornization and we don't know at what data is currently present over there, so we send all the institute specific data to the institute server.

'''
def institute_request(institute_id,institute_hash_dict):
    global dict_hash
    central_new_query_User_tuple = generate(User,institute_id,['id','username','email',  'password' , 'is_active'])
    central_new_query_UserProfile_tuple = generate(UserProfile,institute_id,['id','user_id','name','year_of_birth','gender','level_of_education','mailing_address','allow_certificate'])
    central_new_query_Person_tuple = generate(Person,institute_id,['id','user_id','birth_date','mobile'])
    central_new_query_Institute_Designation_tuple = generate(Institute_Designation,institute_id,['id','user_id','institute_id','role_id','is_approved'])


    #Match hash with current data
    if dict_hash == institute_hash_dict:
        initialize_part(institute_id)
        log.info("Up-to-Date")
        return {"data":"Already Up-to-date"}

    else:

        hash_file_path = "syncing/institute" + str(institute_id) + "/Hash"
        f = open(hash_file_path, 'r')
        temp = f.read()
        dict_hash = ast.literal_eval(temp)
        f.close()

        if dict_hash == institute_hash_dict:
            log.info("Matched From File")
            central_prev_query_User_tuple = read_prev_data_from_file(User,institute_id)
            central_prev_query_UserProfile_tuple = read_prev_data_from_file(UserProfile,institute_id)
            central_prev_query_Person_tuple = read_prev_data_from_file(Person,institute_id)
            central_prev_query_Institute_Designation_tuple = read_prev_data_from_file(Institute_Designation,institute_id)

        else:

            central_prev_query_User_tuple = ()
            central_prev_query_UserProfile_tuple = ()
            central_prev_query_Person_tuple = ()
            central_prev_query_Institute_Designation_tuple = ()

        central_query_User_ins_list, central_query_User_del_list = get_ins_del_list(central_prev_query_User_tuple,central_new_query_User_tuple)
        central_query_UserProfile_ins_list, central_query_UserProfile_del_list = get_ins_del_list(central_prev_query_UserProfile_tuple,central_new_query_UserProfile_tuple)
        central_query_Person_ins_list, central_query_Person_del_list = get_ins_del_list(central_prev_query_Person_tuple,central_new_query_Person_tuple)
        central_query_Institute_Designation_ins_list, central_query_Institute_Designation_del_list = get_ins_del_list(central_prev_query_Institute_Designation_tuple,central_new_query_Institute_Designation_tuple)
           
        temp = {}
        temp['1'] = central_query_User_ins_list
        temp['2'] = central_query_User_del_list
        temp['3'] = central_query_UserProfile_ins_list
        temp['4'] = central_query_UserProfile_del_list
        temp['5'] = central_query_Person_ins_list
        temp['6'] = central_query_Person_del_list
        temp['7'] = central_query_Institute_Designation_ins_list
        temp['8'] = central_query_Institute_Designation_del_list
        log.info("Institute {}".format(temp))
        return temp

#This method is called when an institute requests for the synchronization, we reads all the hashes sent by institute
def sync_institute(request):
    institute_hash_dict = {}
    institute_id = request.GET.get("institute_id")
    log.info("Synchronizing Institute {}".format(institute_id))
    institute_hash_dict['User'] = request.GET.get("User")
    institute_hash_dict['UserProfile'] = request.GET.get("UserProfile")
    institute_hash_dict['Person'] = request.GET.get("Person")
    institute_hash_dict['Institute_Designation'] = request.GET.get("Institute_Designation")
    temp = institute_request(institute_id,institute_hash_dict)
    return JsonResponse(temp)
















