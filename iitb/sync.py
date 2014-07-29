from django.db.models import Q
import commands

def get_filtered_data(table_name,instiute_id,values):
    if table_name == User:
        return User.objects.filter(Q(student_institute__institute_id = institute_id) | Q( institute_designation__institute_id = institute_id) ).values_list(*values)
    else:
        temp = User.objects.filter(Q(student_institute__institute_id = institute_id) | Q( institute_designation__institute_id = institute_id) )
        return table_name.objects.filter(user_id__in = temp ).values_list(*values)

def generate(table_name,instiute_id,values):
    central_prev_quey_table = get_filtered_data(table_name,instiute_id,values)
    central_prev_quey_table_tuple = tuple(central_prev_quey_table)
    central_prev_quey_table_tuple_hash = hash(central_prev_quey_table_tuple)
    path = "syncing/institute" + str(institute_id)
    filename = path + "/" + table_name.__name__ + "_prev" 
    f = open(filename , 'w')
    f.write(str(central_prev_quey_table_tuple))
    f.close()

def initialize(institute_id):
    per = "sudo -u edxapp "
    path = " syncing/institute" + str(institute_id)
    commands.getoutput(per + "mkdir" + path)
    commands.getoutput(per + "touch" + path + "/User_prev")
    commands.getoutput(per + "touch" + path + "/UserProfile_prev")
    commands.getoutput(per + "touch" + path + "/Person_prev")
    commands.getoutput(per + "touch" + path + "/Institute_Designation_prev")
    generate(User,institute_id,['id','username','email',  'password' , 'is_active'])
    generate(UserProfile,institute_id,['id'])
    generate(Person,institute_id,['id'])
    generate(Institute_Designation,institute_id,['id'])












central_prev_quey_user = get_filtered_data(User,1,['id','username','email',  'password' , 'is_active'])
central_prev_quey_user_tuple = tuple(central_prev_quey_user)
central_prev_quey_user_tuple_hash = hash(central_prev_quey_user_tuple)
f = open('auth_user_prev' , 'w')
f.write(str(central_prev_quey_user_tuple))
f.close()





central_prev_quey_user = User.objects.filter(id__lte = 2 ).values_list('id' , 'username' , 'email' , 'password' , 'is_active')
central_prev_quey_user_tuple = tuple(central_prev_quey_user)
central_prev_quey_user_tuple_hash = hash(central_prev_quey_user_tuple)
f = open('test_file' , 'a')
f.write(str(central_prev_quey_user_tuple))
f.close()



Local Request :


central_new_quey_user = User.objects.filter(id__lte = 8 ).values_list('id' , 'username' , 'email' , 'password' , 'is_active')
central_new_quey_user_tuple = tuple(central_new_quey_user)
central_new_quey_user_tuple_hash = hash(central_new_quey_user_tuple)




Check with new hash if hash different :

Read hash from prev 
if matches:

import ast
f = open('test_file' , 'r')
f1 = f.read()
central_prev_quey_user_tuple = ast.literal_eval(f1)
f1.close()

central_prev_query_user_list  = list( list(i) for i in central_prev_quey_user_tuple )
central_new_query_user_list  = list( list(i) for i in central_new_quey_user_tuple )

central_query_user_ins_list = [ x for x in central_new_query_user_list if x not in central_prev_query_user_list ]
central_query_user_del_list = [ x for x in central_prev_query_user_list if x not in central_new_query_user_list ]

for x in central_query_user_del_list:
    for y in central_query_user_ins_list:
        if x[0] == y[0]:
             central_query_user_del_list.remove(x)











##Send to local



for item in central_query_user_del_list:
    temp = User ( id = item[0] )
    temp.delete()


for item in central_query_user_ins_list:
     temp = User ( id =item[0] , username = item[1] , email = item[2] , password = item[3] , is_active = item[4] )
     temp.save()













































import ast


f = open('test_file' , 'a')
f.write(str(central_prev_quey_user_tuple))
f.close()


f = open('test_file' , 'r')
f1 = f.read()
f1 = ast.literal_eval(f1)
f1.close()











































# tuple to list
data  = list( list(i) for i in central_prev_quey_user_tuple )





#    UserProfile_table = UserProfile.objects.filter( user__id = User_table)
#    Person_table = Person.objects.filter( user__id = User_table)
#central_prev_quey_user = User.objects.filter(id__lte = 2 ).values_list('id' , 'username' , 'email' , 'password' , 'is_active')

values = ['id','username','email',  'password' , 'is_active']
