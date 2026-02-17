from django.contrib import admin

from apps.feature_flags.models import FeatureFlag, FlagVariant


class FlagVariantInline(admin.TabularInline):
    model = FlagVariant
    extra = 0


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = (
        "key", "name", "flag_type", "status", "risk_level",
        "environment", "is_enabled", "kill_switch", "version", "created_at",
    )
    list_filter = ("status", "flag_type", "risk_level", "is_enabled", "kill_switch")
    search_fields = ("key", "name")
    readonly_fields = ("version", "created_at", "updated_at")
    inlines = [FlagVariantInline]
