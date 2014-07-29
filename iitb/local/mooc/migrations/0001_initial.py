# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'State'
        db.create_table('mooc_state', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=45)),
        ))
        db.send_create_signal('mooc', ['State'])

        # Adding model 'City'
        db.create_table('mooc_city', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=45)),
            ('state', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.State'])),
        ))
        db.send_create_signal('mooc', ['City'])

        # Adding model 'Accreditation'
        db.create_table('mooc_accreditation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=10)),
        ))
        db.send_create_signal('mooc', ['Accreditation'])

        # Adding model 'Role'
        db.create_table('mooc_role', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=30)),
        ))
        db.send_create_signal('mooc', ['Role'])

        # Adding model 'Status'
        db.create_table('mooc_status', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
        ))
        db.send_create_signal('mooc', ['Status'])

        # Adding model 'Course'
        db.create_table('mooc_course', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
        ))
        db.send_create_signal('mooc', ['Course'])

        # Adding model 'Institute_Status'
        db.create_table('mooc_institute_status', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
        ))
        db.send_create_signal('mooc', ['Institute_Status'])

        # Adding model 'Institute_Registration'
        db.create_table('mooc_institute_registration', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100, db_index=True)),
            ('state', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.State'])),
            ('city', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.City'])),
            ('pincode', self.gf('django.db.models.fields.IntegerField')()),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('website', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('is_parent', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('status', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.Institute_Status'])),
            ('remarks', self.gf('django.db.models.fields.CharField')(max_length=100, null=True)),
        ))
        db.send_create_signal('mooc', ['Institute_Registration'])

        # Adding model 'Student_Institute'
        db.create_table('mooc_student_institute', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('institute', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.Institute_Registration'])),
            ('active_from', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('active_upto', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.Institute_Status'])),
        ))
        db.send_create_signal('mooc', ['Student_Institute'])

        # Adding model 'Institute_Course'
        db.create_table('mooc_institute_course', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('course', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.Course'])),
            ('institute', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.Institute_Registration'])),
            ('is_approved', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('mooc', ['Institute_Course'])

        # Adding model 'Course_Registration'
        db.create_table('mooc_course_registration', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('institute', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.Institute_Registration'])),
            ('course', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.Course'])),
            ('status', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.Institute_Status'])),
            ('role', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.Role'])),
            ('is_approved', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('mooc', ['Course_Registration'])

        # Adding model 'Hierarchy'
        db.create_table('mooc_hierarchy', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.Institute_Registration'])),
            ('child_id', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('mooc', ['Hierarchy'])

        # Adding model 'Person'
        db.create_table('mooc_person', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='person', unique=True, to=orm['auth.User'])),
            ('birth_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('mobile', self.gf('django.db.models.fields.BigIntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('mooc', ['Person'])

        # Adding model 'Institute_Designation'
        db.create_table('mooc_institute_designation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('institute', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.Institute_Registration'])),
            ('role', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.Role'])),
            ('is_approved', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('mooc', ['Institute_Designation'])

        # Adding model 'Institute_Accreditation'
        db.create_table('mooc_institute_accreditation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('accreditation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.Accreditation'])),
            ('institute', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mooc.Institute_Registration'])),
        ))
        db.send_create_signal('mooc', ['Institute_Accreditation'])


    def backwards(self, orm):
        # Deleting model 'State'
        db.delete_table('mooc_state')

        # Deleting model 'City'
        db.delete_table('mooc_city')

        # Deleting model 'Accreditation'
        db.delete_table('mooc_accreditation')

        # Deleting model 'Role'
        db.delete_table('mooc_role')

        # Deleting model 'Status'
        db.delete_table('mooc_status')

        # Deleting model 'Course'
        db.delete_table('mooc_course')

        # Deleting model 'Institute_Status'
        db.delete_table('mooc_institute_status')

        # Deleting model 'Institute_Registration'
        db.delete_table('mooc_institute_registration')

        # Deleting model 'Student_Institute'
        db.delete_table('mooc_student_institute')

        # Deleting model 'Institute_Course'
        db.delete_table('mooc_institute_course')

        # Deleting model 'Course_Registration'
        db.delete_table('mooc_course_registration')

        # Deleting model 'Hierarchy'
        db.delete_table('mooc_hierarchy')

        # Deleting model 'Person'
        db.delete_table('mooc_person')

        # Deleting model 'Institute_Designation'
        db.delete_table('mooc_institute_designation')

        # Deleting model 'Institute_Accreditation'
        db.delete_table('mooc_institute_accreditation')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'mooc.accreditation': {
            'Meta': {'object_name': 'Accreditation'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        },
        'mooc.city': {
            'Meta': {'object_name': 'City'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '45'}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.State']"})
        },
        'mooc.course': {
            'Meta': {'object_name': 'Course'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'mooc.course_registration': {
            'Meta': {'object_name': 'Course_Registration'},
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.Course']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institute': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.Institute_Registration']"}),
            'is_approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'role': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.Role']"}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.Institute_Status']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'mooc.hierarchy': {
            'Meta': {'object_name': 'Hierarchy'},
            'child_id': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent_id': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.Institute_Registration']"})
        },
        'mooc.institute_accreditation': {
            'Meta': {'object_name': 'Institute_Accreditation'},
            'accreditation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.Accreditation']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institute': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.Institute_Registration']"})
        },
        'mooc.institute_course': {
            'Meta': {'object_name': 'Institute_Course'},
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.Course']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institute': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.Institute_Registration']"}),
            'is_approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'mooc.institute_designation': {
            'Meta': {'object_name': 'Institute_Designation'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institute': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.Institute_Registration']"}),
            'is_approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'role': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.Role']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'mooc.institute_registration': {
            'Meta': {'object_name': 'Institute_Registration'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'city': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.City']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_parent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'pincode': ('django.db.models.fields.IntegerField', [], {}),
            'remarks': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.State']"}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.Institute_Status']"}),
            'website': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'mooc.institute_status': {
            'Meta': {'object_name': 'Institute_Status'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'})
        },
        'mooc.person': {
            'Meta': {'object_name': 'Person'},
            'birth_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mobile': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'person'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'mooc.role': {
            'Meta': {'object_name': 'Role'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'mooc.state': {
            'Meta': {'object_name': 'State'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '45'})
        },
        'mooc.status': {
            'Meta': {'object_name': 'Status'},
            'description': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mooc.student_institute': {
            'Meta': {'object_name': 'Student_Institute'},
            'active_from': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'active_upto': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institute': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.Institute_Registration']"}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['mooc.Institute_Status']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['mooc']