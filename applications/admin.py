from django.contrib import admin
from .models import College, Program, Recommender, Document, Application, Notification

admin.site.register(College)
admin.site.register(Program)
admin.site.register(Recommender)
admin.site.register(Document)
admin.site.register(Application)
admin.site.register(Notification)
