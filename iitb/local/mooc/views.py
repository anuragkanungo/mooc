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
import requests
from collections import defaultdict
from pytz import UTC
from student.models import *
from mooc.models import *
import hashlib
import ast
from functools import wraps
import errno
import os
import signal
from django.conf import settings
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.models import User, AnonymousUser
from mooc.models import Institute_Registration, State, City, Institute_Accreditation, Accreditation, Institute_Designation, Role, Institute_Status, Student_Institute, Institute_Course
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
from django.db.models import Q
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



log = logging.getLogger("edx.student")
AUDIT_LOG = logging.getLogger("audit")

Article = namedtuple('Article', 'title url author image deck publication publish_date')
ReverifyInfo = namedtuple('ReverifyInfo', 'course_id course_name course_number date status display')  # pylint: disable=C0103


class TimeoutError(Exception):
    pass

def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator


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


    required_post_vars = ['name', 'state', 'city', 'pincode', 'address', 'website', 'headName', 'headEmail', 'headMobile',            'rccName', 'rccEmail', 'rccMobile']


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
    Student_Institute_Objects = Student_Institute.objects.filter(institute_id=institute)
    
    context = { 'Student_Institute_Objects' : Student_Institute_Objects,
                'rolename': rolename,
                }
    return render_to_response('ic_approve_students.html',context)

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

    Institute_Course_Objects = Institute_Course.objects.filter(institute_id=institute)
    context = { 'rolename': rolename, 'Institute_Course_Objects' : Institute_Course_Objects,
                }
 
    return render_to_response('ic_enrolled_courses.html',context)


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
    """ When Student Selects an Institute. """
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
    This view will allow the central coordinater to view data of a particluar institute.
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


#Synchronization

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

def get_hash():
    dict_hash = {}
    temp = User.objects.filter(Q(is_superuser =0) & ~Q( id = 1))
    log.info("{}".format(temp))
    User_hash = hashlib.md5(str(tuple(User.objects.filter( Q(is_superuser =0) & ~Q( id = 1)).values_list('id','username','email','password','is_active')))).hexdigest()


    UserProfile_hash = hashlib.md5(str(tuple(UserProfile.objects.filter(user__id__in=temp).values_list('id','user_id','name','year_of_birth','gender','level_of_education','mailing_address','allow_certificate')))).hexdigest()

    temp_str = str(tuple(Person.objects.filter(user__id__in=temp).values_list('id','user_id','birth_date','mobile')))
    if "datetime.date" in temp_str:
        temp_str = re.sub(r'(datetime.date\()(\d+)(, )(\d+)(, )(\d+)(\))',r'"\2-\4-\6"',temp_str)
        temp_str = ast.literal_eval(temp_str)
    Person_hash = hashlib.md5(str(temp_str)).hexdigest()
    print temp_str


    Institute_Designation_hash = hashlib.md5(str(tuple(Institute_Designation.objects.filter(user__id__in=temp).values_list('id','user_id','institute_id','role_id','is_approved')))).hexdigest()
    dict_hash["User"]= User_hash
    dict_hash["UserProfile"]= UserProfile_hash
    dict_hash["Person"]= Person_hash
    dict_hash["Institute_Designation"]= Institute_Designation_hash
    return dict_hash


def insert_data(central_query_User_ins_list,central_query_UserProfile_ins_list,central_query_Person_ins_list,central_query_Institute_Designation_ins_list):
    for item in central_query_User_ins_list:
        temp = User(id=item[0],username=item[1],email=item[2],password=item[3],is_active=item[4])
        temp.save()
    
    for item in central_query_UserProfile_ins_list:
        temp = UserProfile(id=item[0],user_id=item[1],name=item[2], year_of_birth=item[3] ,gender=item[4], level_of_education= item[5], mailing_address=item[6],allow_certificate=item[7])
        temp.save()
    
    for item in central_query_Person_ins_list:
        temp = Person(id=item[0],user_id=item[1],birth_date=item[2], mobile=item[3]) 
        temp.save()
    
    for item in central_query_Institute_Designation_ins_list:
        temp = Institute_Designation(id=item[0],user_id=item[1],institute_id=item[2],  role_id=item[3] , is_approved=item[4]) 
        temp.save()


def delete_data(central_query_User_del_list,central_query_UserProfile_del_list,central_query_Person_del_list,central_query_Institute_Designation_del_list):
    for item in central_query_Institute_Designation_del_list:
        temp = Institute_Designation(id=item[0]) 
        temp.delete()
    
    for item in central_query_Person_del_list:
        temp = Person(id=item[0]) 
        temp.delete()
  
    for item in central_query_UserProfile_del_list:
        temp = UserProfile(id=item[0])
        temp.delete()
    
    for item in central_query_User_del_list:
        temp = User(id=item[0])
        temp.delete()

#def initialize():
#    insert_data(central_query_User_ins_list,central_query_UserProfile_ins_list,central_query_Person_ins_list,central_query_Institute_Designation_ins_list)#
#    delete_data(central_query_User_del_list,central_query_UserProfile_del_list,central_query_Person_del_list,central_query_Institute_Designation_del_list)

@timeout(900, os.strerror(errno.ETIMEDOUT))
def sync_institute(request):
    data = get_hash()
    insti_id = Institute_Registration.objects.all()[0].id
    data['institute_id'] = insti_id
    r =requests.get("http://iitbombayx.cse.iitb.ac.in/sync" , params=data)
    log.info("{}".format(r.url))
    temp = r.json()
    dict_string = ""
    for key,val in temp.iteritems():
        dict_string = dict_string + str(key) + str(val)
    
    bytes = len(dict_string)/8
    log.info("Data Recieved {}".format(dict_string))
    try:
        if temp["data"]:
            #return HttpResponse(temp["data"] + str(bits))
            context = { "data" : temp["data"] , "bytes" : bytes }
            return render_to_response('sync.html',context)
    except:
        central_query_User_ins_list = temp['1']
        central_query_UserProfile_ins_list = temp['3']
        central_query_Person_ins_list = temp['5']
        central_query_Institute_Designation_ins_list = temp['7']
        central_query_User_del_list = temp['2']
        central_query_UserProfile_del_list = temp['4']
        central_query_Person_del_list = temp['6']
        central_query_Institute_Designation_del_list = temp['8']

        insert_data(central_query_User_ins_list,central_query_UserProfile_ins_list,central_query_Person_ins_list,central_query_Institute_Designation_ins_list)

        delete_data(central_query_User_del_list,central_query_UserProfile_del_list,central_query_Person_del_list,central_query_Institute_Designation_del_list)
        #sync_institute(request)
        #return HttpResponse("Done" + str(bits))
        context = { "data" : "Sync Completed" , "bytes" :bytes }
        return render_to_response('sync.html',context)




@timeout(900, os.strerror(errno.ETIMEDOUT))
def sync_institute_new(request):
    data = get_hash()
    insti_id = Institute_Registration.objects.all()[0].id
    data['institute_id'] = insti_id
    r =requests.get("http://iitbombayx.cse.iitb.ac.in/sync_new" , params=data)
    log.info("{}".format(r.url))
    temp = r.json()
    dict_string = ""
    for key,val in temp.iteritems():
        dict_string = dict_string + str(key) + str(val)
    
    bytes = len(dict_string)/8
    log.info("Data Recieved {}".format(dict_string))
    try:
        if temp["data"]:
            #return HttpResponse(temp["data"] + str(bits))
            context = { "data" : temp["data"] , "bytes" : bytes }
            return render_to_response('sync.html',context)
    except:
        central_query_User_ins_list = temp['1']
        central_query_UserProfile_ins_list = temp['3']
        central_query_Person_ins_list = temp['5']
        central_query_Institute_Designation_ins_list = temp['7']
        central_query_User_del_list = temp['2']
        central_query_UserProfile_del_list = temp['4']
        central_query_Person_del_list = temp['6']
        central_query_Institute_Designation_del_list = temp['8']

        insert_data(central_query_User_ins_list,central_query_UserProfile_ins_list,central_query_Person_ins_list,central_query_Institute_Designation_ins_list)

        delete_data(central_query_User_del_list,central_query_UserProfile_del_list,central_query_Person_del_list,central_query_Institute_Designation_del_list)
        #sync_institute(request)
        #return HttpResponse("Done" + str(bits))
        context = { "data" : "Sync Completed" , "bytes" :bytes }
        return render_to_response('sync.html',context)
