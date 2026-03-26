from django.contrib import admin
from .models import (
    Box,
    Genotype,
    Membership,
    Mouse,
    MouseObservation,
    Project,
    Request,
    Strain,
    StudyPlan,
    Notification,
)

admin.site.register(Box)
admin.site.register(Genotype)
admin.site.register(Membership)
admin.site.register(Mouse)
admin.site.register(MouseObservation)
admin.site.register(Project)
admin.site.register(Request)
admin.site.register(Strain)
admin.site.register(StudyPlan)
admin.site.register(Notification)
