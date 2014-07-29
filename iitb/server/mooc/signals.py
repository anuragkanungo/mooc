from django.db import models 
from django.forms import ModelForm
from django.db.models import Count
from datetime import datetime
import uuid
from django.contrib.auth.models import User
import json
from django.db.models import Q
from mooc.models import Person, Institute_Designation, Student_Institute, Institute_Registration, Institute_Sync, Institute_Status
from student.models import UserProfile

#######Signals################################
import logging
from django.db.models import signals

log = logging.getLogger("synchronization")

prev_list = []

def get_filtered_data(institute_id,model_name):
    temp = User.objects.filter(Q(student_institute__institute_id = institute_id) | Q( institute_designation__institute_id = institute_id) )
    if model_name == User:
        return temp.values_list('id')
    else:
        return model_name.objects.filter(user__id__in = temp ).values_list('id')

def save_old_value(sender, instance, *args, **kwargs):
    global prev_list
    print "Pre save emited for", instance
    if instance.id:
        if instance.__class__.__name__ == "User":
            instance.old_value = instance.__class__.objects.filter(id=instance.id).values_list('id','username','email',  'password' , 'is_active')
        elif instance.__class__.__name__ == "Person":
            instance.old_value = instance.__class__.objects.filter(id=instance.id).values_list('id','user_id','birth_date','mobile')
        else:
            instance.old_value = instance.__class__.objects.filter(id=instance.id).values_list()
        prev_list = list(instance.old_value[0])
        #print prev_list
        log.info("Old {}".format(prev_list))


def save_new_value(sender, instance, created, **kwargs):
    global prev_list
    print "Post save emited for", instance
    if instance.id:
        if instance.__class__.__name__ == "User":
            instance.new_value = instance.__class__.objects.filter(id=instance.id).values_list('id','username','email','password', 'is_active')
        elif instance.__class__.__name__ == "Person":
            instance.new_value = instance.__class__.objects.filter(id=instance.id).values_list('id','user_id','birth_date','mobile')
        else:
            instance.new_value = instance.__class__.objects.filter(id=instance.id).values_list()

        new_list = list(instance.new_value[0])
        #print new_list
        log.info("New {}".format(new_list))
        flag = 0
        if not prev_list == new_list:
            log.info("Needs to be Synchronized")
            flag = 1
        elif created:
            log.info("Needs to be Synchronized -- Created")
            flag = 1

        if flag == 1:
            print " Need to check that record belong to which institutes"
            log.info(" Need to check that record belong to which institutes")
            for item in Institute_Registration.objects.all().values_list('id'):
                for institute_id in item:
                    data = get_filtered_data(institute_id,sender)
                    for temp_item in data:
                            log.info(" Instance {}".format(temp_item))
                            log.info(" Instanceid {}".format(instance.id))
                            if instance.id in temp_item:
                                print institute_id , instance.__class__.__name__ , instance.id
                                log.info(" Instance {}".format(institute_id))
                                try:
                                    log.info(" Institute {}".format(institute_id))
                                    status=Institute_Status.objects.filter(name="Approved")[0].id 
                                    if (instance.__class__.__name__ == "Institute_Designation" or instance.__class__.__name__ == "Student_Institute") and instance.status_id == status:
                                        Institute_Sync(institute_id = institute_id , model_name= "User" , change_type  = False, record = instance.user.id).save()
                                        Institute_Sync(institute_id = institute_id , model_name= "UserProfile" , change_type  = False, record = instance.user.profile.id).save()
                                        Institute_Sync(institute_id = institute_id , model_name= "Person" , change_type  = False, record = instance.user.person.id).save()
                                    if not instance.__class__.__name__ == "Student_Institute":
                                        Institute_Sync(institute_id = institute_id , model_name= instance.__class__.__name__ , change_type  = False, record = instance.id).save()
                                except:
                                    continue





def delete_value(sender, instance, *args, **kwargs):
    print "Post delete emited for", instance
    if instance.id:
        print " Need to check that record belong to which institutes"
        log.info(" Need to check that record belong to which institutes")
        for item in Institute_Registration.objects.all().values_list('id'):
            for institute_id in item:
                data = get_filtered_data(institute_id,sender)
                for temp_item in data:
                        log.info(" Instance {}".format(temp_item))
                        log.info(" Instanceid {}".format(instance.id))
                        if not instance.id in temp_item:
                            print institute_id , instance.__class__.__name__ , instance.id
                            log.info(" Instance {}".format(institute_id))
                            try:
                                if not instance.__class__.__name__ == "Student_Institute":
                                    Institute_Sync(institute_id = institute_id , model_name= instance.__class__.__name__ , change_type  = True, record = instance.id).save()
                                log.info(" Institute {}".format(institute_id))
                                if instance.__class__.__name__ == "Institute_Designation" or instance.__class__.__name__ == "Student_Institute":
                                    Institute_Sync(institute_id = institute_id , model_name= "Person" , change_type  = True, record = instance.user.person.id).save()
                                    Institute_Sync(institute_id = institute_id , model_name= "UserProfile" , change_type  = True, record = instance.user.profile.id).save()
                                    Institute_Sync(institute_id = institute_id , model_name= "User" , change_type  = True, record = instance.user.id).save()
                            except:
                                continue




signals.pre_save.connect(save_old_value,sender=User)
signals.post_save.connect(save_new_value,sender=User)

signals.pre_save.connect(save_old_value,sender=UserProfile)
signals.post_save.connect(save_new_value,sender=UserProfile)

signals.pre_save.connect(save_old_value,sender=Person)
signals.post_save.connect(save_new_value,sender=Person)

signals.pre_save.connect(save_old_value,sender=Institute_Designation)
signals.post_save.connect(save_new_value,sender=Institute_Designation)

signals.pre_save.connect(save_old_value,sender=Student_Institute)
signals.post_save.connect(save_new_value,sender=Student_Institute)



#signals.post_delete.connect(delete_value,sender=User)
#signals.post_delete.connect(delete_value,sender=UserProfile)
#signals.post_delete.connect(delete_value,sender=Person)
#signals.post_delete.connect(delete_value,sender=Student_Institute)
#signals.post_delete.connect(delete_value,sender=Institute_Designation)
