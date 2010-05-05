# encoding: utf-8

from django.contrib import admin
from stapler.models import Staplerjob

class StaplerjobAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('movement_id', 'from_location', 'to_location', 'status', 'user')
    list_filter = ('status', 'user')
    search_fields = ('movement_id', )

admin.site.register(Staplerjob, StaplerjobAdmin)
