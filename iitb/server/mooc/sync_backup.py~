from django.core.management import call_command
from django.db.models import Q
import commands
from student.models import *
from mooc.models import *
import ast
import hashlib

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
















