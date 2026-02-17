from django.contrib import admin

from apps.tenants.models import Environment, Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "subscription_plan", "is_active", "created_at")
    list_filter = ("subscription_plan", "is_active")
    search_fields = ("name", "slug")


@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "is_active", "created_at")
    list_filter = ("name", "is_active")
