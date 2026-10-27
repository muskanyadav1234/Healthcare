from django.contrib import admin

from .models import Doctor, Patient, PatientDoctorMapping

admin.site.register(Patient)
admin.site.register(Doctor)
admin.site.register(PatientDoctorMapping)
