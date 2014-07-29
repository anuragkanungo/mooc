'''
django admin pages for mooc model
'''

from mooc.models import Role, Institute_Accreditation , Accreditation , Person , State , City , Institute_Designation , Institute_Registration, Student_Institute , Status, Course_Registration, Hierarchy, Institute_Status, Central_Coordinator, Institute_Course
from ratelimitbackend import admin


class PersonAdmin(admin.ModelAdmin):
    list_display = ('user', 'birth_date', 'mobile')

class Institute_AccreditationAdmin(admin.ModelAdmin):
    list_display = ('accreditation', 'institute')
    readonly_fields = ['accreditation','institute']
    ordering = ('-accreditation',)
    ordering = ('-institute',)


class Institute_AccreditationInline(admin.StackedInline):
	model=Institute_Accreditation
	readonly_fields = ['accreditation']
	fieldsets = (
       		 (None, {
          		  'fields': ['accreditation']
        	}),
    	)
	extra=0


class Institute_DesignationAdmin(admin.ModelAdmin):
    list_display = ('user', 'institute', 'role','is_approved')
    ordering = ('-role',)
    ordering = ('-institute',)


class Institute_DesignationInline(admin.StackedInline):
	model=Institute_Designation
	readonly_fields = ["user","role"]
	fieldsets = (
       		 (None, {
          		  'fields': ['user','role','is_approved']
        	}),
    	)
	extra=0	


class Institute_RegistrationAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'state')
    readonly_fields = ("name","state", "city","pincode","address","website","status","remarks")
    inlines = [
        Institute_AccreditationInline,
	Institute_DesignationInline,
    ]

    fieldsets = (
        (None, {
            'fields': ['name', 'state', 'city',"pincode","address","website","is_parent","status","remarks"]
        }),
    )
    ordering = ('-name',)
    ordering = ('-city',)


admin.site.register(Central_Coordinator) 
admin.site.register(Institute_Course)
admin.site.register(Person, PersonAdmin)
admin.site.register(Role)
admin.site.register(Institute_Designation,Institute_DesignationAdmin)

admin.site.register(Institute_Registration, Institute_RegistrationAdmin)
admin.site.register(Institute_Accreditation, Institute_AccreditationAdmin)
admin.site.register(Institute_Status)
admin.site.register(Hierarchy)

admin.site.register(Student_Institute)
admin.site.register(Course_Registration)
admin.site.register(Status)



admin.site.register(Accreditation)
admin.site.register(City)
admin.site.register(State)
