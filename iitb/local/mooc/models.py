from django.db import models 
from django.forms import ModelForm
from django.db.models import Count
from datetime import datetime
import uuid
from django.contrib.auth.models import User
import json

class Central_Coordinator(models.Model):
      '''
      This stores the details about which user has which designation related to central server.
      '''
      user = models.ForeignKey(User, db_index=True)
      is_approved = models.BooleanField()
       
      def __str__(self):
	 return str(self.user)

class State(models.Model):

       ''' 
       Model to store states of the country
       '''
       name = models.CharField(max_length=45, unique=True)
     
       def __str__(self):
	 return self.name


class City(models.Model):

       
       ''' 
       Model to store cities and also to which state it belongs
       '''
       name = models.CharField(max_length=45)
       state = models.ForeignKey(State, db_index=True)

       def __str__(self):
	 return self.name

class Accreditation(models.Model):

       '''
       This would store all the accreditation that an institute can have.
       '''
       name = models.CharField( max_length=10)

       def __str__(self):
	 return self.name

       

class Role(models.Model):

      '''
      This would store all the roles that an user can have.
      '''
      name = models.CharField(max_length=30, unique=True)
    
      def __str__(self):
	 return self.name

class Status(models.Model):
      description = models.CharField(max_length=20, unique=True)

      def __str__(self):
	 return self.description
      
class Course(models.Model):
     
      '''
      This would store all the courses created.
      '''
      name = models.CharField(max_length=100, unique=True)

      def __str__(self):
	 return str(self.name)

class Institute_Status(models.Model):

       ''' 
       Model to store 
       '''
       name = models.CharField(max_length=20, unique=True)
     
       def __str__(self):
	 return self.name

class Institute_Registration(models.Model):

     ''' 
     Model to store institute details when an institute registers
     It stores the name , city , state , address, pincode , website.
     status and is_parent are for the use of central coordinator
     After verification , if institute is legit and met the requirement criteria the 
     central coordinator will set status to approved by default it is pending. 
     If institute is a university( Parent of various other institutions)
     then is_parent is set to True by central coordiantor.

     '''


     name = models.CharField(max_length=100, db_index=True, unique=True)
     state = models.ForeignKey(State )
     city = models.ForeignKey(City )
     pincode = models.IntegerField()
     address = models.CharField(max_length=150)
     website = models.CharField(max_length=50)
     is_parent = models.BooleanField()
     status = models.ForeignKey(Institute_Status)
     remarks = models.CharField(max_length=100, null=True)

     def __str__(self):
	 return self.name



class Student_Institute(models.Model):

      '''
      This stores information about the student i.e. when for which period the student is active with an institute.
      A student can belong to multiple institutes at the same time.
      '''
      user = models.ForeignKey(User, db_index=True)
      institute = models.ForeignKey(Institute_Registration, db_index=True)
      active_from = models.DateTimeField(auto_now_add=True, null=True)
      active_upto = models.DateTimeField(auto_now_add=True, null=True)
      status = models.ForeignKey(Institute_Status)
     
      def __str__(self):
	 return str(self.user)


class Institute_Course(models.Model):
     
      '''
      This stores which insitute is allowed to participate in which courses.
      '''
      course = models.ForeignKey(Course, db_index=True)
      institute = models.ForeignKey(Institute_Registration, db_index=True)
      is_approved = models.BooleanField(default=False)

      def __str__(self):
	 return str(self.institute)

class Course_Registration(models.Model):

      '''
      This stores the details when a user register with a course under the institute.
      '''

      user = models.ForeignKey(User, db_index=True)
      institute = models.ForeignKey(Institute_Registration, db_index=True)
      course = models.ForeignKey(Course, db_index=True)
      status = models.ForeignKey(Institute_Status, db_index=True)
      role = models.ForeignKey(Role, db_index=True)
      is_approved = models.BooleanField()

      def __str__(self):
	 return "{0}, {1}".format(str(self.user) , str(self.institute))
       

class Hierarchy(models.Model):
      parent_id = models.ForeignKey(Institute_Registration, db_index=True)
      child_id = models.IntegerField()

      def __str__(self):
	 return "{0}, {1}".format(str(self.parent_id) , str(self.child_id))
       

class Person(models.Model):

      '''
      This would store the additional details of the user while registration. Because auth_user and auth_userprofile
      doesn't store birth date and mobile number of the user.
      '''
      user = models.OneToOneField(User, unique=True, db_index=True, related_name='person')
      birth_date = models.DateField(blank=True, null=True)
      mobile = models.BigIntegerField(blank=True, null=True)

      def get_meta(self):
        js_str = self.meta
        if not js_str:
            js_str = dict()
        else:
            js_str = json.loads(self.meta)

        return js_str

      def set_meta(self, js):
        self.meta = json.dumps(js)

      def __str__(self):
	 return str(self.user)


class Institute_Designation(models.Model):

      '''
      This stores the details about which user has which designation related to that institute.
      '''
      user = models.ForeignKey(User, db_index=True)
      institute = models.ForeignKey(Institute_Registration, db_index=True)
      role = models.ForeignKey(Role, db_index=True)
      is_approved = models.BooleanField()
       
      def __str__(self):
	 return str(self.institute)


       
class Institute_Accreditation(models.Model):

      '''
      This stores the details which institute have which accreditaitons. 
      '''
      accreditation = models.ForeignKey(Accreditation, db_index=True)
      institute = models.ForeignKey(Institute_Registration, db_index=True)

      def __str__(self):
	 return str(self.institute)

