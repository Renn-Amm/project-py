import json
import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import UserRole
from apps.analytics.models import EvaluationEvent
from apps.audit.models import AuditLog
from apps.feature_flags.models import FeatureFlag, FlagStatus
from apps.feature_flags.services import FeatureFlagService, FlagVariantService
from apps.policies.models import ApprovalRequest, ApprovalStatus
from apps.policies.services import ApprovalService
from apps.targeting.models import TargetingRule
from apps.tenants.models import Environment

logger = logging.getLogger(__name__)

STALE_DAYS = getattr(settings, "STALE_FLAG_DAYS", 30)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_tenant(request):
    return getattr(request.user, "tenant", None)


def _get_environments(request):
    tenant = _get_tenant(request)
    if not tenant:
        return Environment.objects.none()
    return tenant.environments.all()


def _require_role(request, minimum_role):
    if not request.user.has_role_level(minimum_role):
        return HttpResponseForbidden("Insufficient permissions.")
    return None


def _get_tenant_flags(request):
    tenant = _get_tenant(request)
    if not tenant:
        return FeatureFlag.objects.none()
    return (
        FeatureFlag.objects
        .filter(environment__tenant=tenant)
        .select_related("environment", "depends_on", "created_by")
        .prefetch_related("variants", "targeting_rules")
    )


# ---------------------------------------------------------------------------
# Auth Views
# ---------------------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard_home")
    if request.method == "POST":
        email = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            next_url = request.POST.get("next") or request.GET.get("next") or "dashboard_home"
            return redirect(next_url)
        return render(request, "dashboard/login.html", {"form": {"errors": True}})
    return render(request, "dashboard/login.html", {"next": request.GET.get("next", "")})


@require_POST
@login_required
def logout_view(request):
    logout(request)
    return redirect("dashboard_login")


# ---------------------------------------------------------------------------
# Dashboard Home
# ---------------------------------------------------------------------------

@login_required
def dashboard_home(request):
    tenant = _get_tenant(request)
    if not tenant:
        return render(request, "dashboard/home.html", {"stats": {}, "recent_logs": [], "env_breakdown": []})

    flags = FeatureFlag.objects.filter(environment__tenant=tenant)
    stale_cutoff = timezone.now() - timedelta(days=STALE_DAYS)

    stats = {
        "total_flags": flags.count(),
        "active_enabled": flags.filter(status=FlagStatus.ACTIVE, is_enabled=True).count(),
        "expired": sum(1 for f in flags.only("expire_at") if f.is_expired),
        "stale": flags.filter(
            status=FlagStatus.ACTIVE,
            last_evaluated_at__isnull=False,
            last_evaluated_at__lt=stale_cutoff,
        ).count() + flags.filter(
            status=FlagStatus.ACTIVE,
            last_evaluated_at__isnull=True,
            created_at__lt=stale_cutoff,
        ).count(),
        "pending_approvals": ApprovalRequest.objects.filter(
            flag__environment__tenant=tenant,
            status=ApprovalStatus.PENDING,
        ).count(),
    }

    recent_logs = (
        AuditLog.objects
        .filter(tenant=tenant)
        .select_related("actor")
        .order_by("-timestamp")[:10]
    )

    env_breakdown = (
        flags
        .values("environment__name")
        .annotate(count=Count("id"))
        .order_by("environment__name")
    )
    env_breakdown = [{"name": e["environment__name"], "count": e["count"]} for e in env_breakdown]

    return render(request, "dashboard/home.html", {
        "stats": stats,
        "recent_logs": recent_logs,
        "env_breakdown": env_breakdown,
        "environments": _get_environments(request),
    })


# ---------------------------------------------------------------------------
# Feature Flags List
# ---------------------------------------------------------------------------

@login_required
def flag_list_view(request):
    qs = _get_tenant_flags(request)

    # Filters
    env = request.GET.get("environment", "")
    status_filter = request.GET.get("status", "")
    risk = request.GET.get("risk_level", "")
    search = request.GET.get("search", "").strip()

    if env:
        qs = qs.filter(environment__name=env)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if risk:
        qs = qs.filter(risk_level=risk)
    if search:
        qs = qs.filter(Q(key__icontains=search) | Q(name__icontains=search))

    stale_cutoff = timezone.now() - timedelta(days=STALE_DAYS)
    flags = list(qs)
    for flag in flags:
        flag.is_stale = (
            flag.status == FlagStatus.ACTIVE
            and (
                (flag.last_evaluated_at and flag.last_evaluated_at < stale_cutoff)
                or (not flag.last_evaluated_at and flag.created_at < stale_cutoff)
            )
        )

    return render(request, "dashboard/flags.html", {
        "flags": flags,
        "environments": _get_environments(request),
        "selected_environment": env,
    })


# ---------------------------------------------------------------------------
# Flag Create
# ---------------------------------------------------------------------------

@login_required
def flag_create_view(request):
    perm = _require_role(request, UserRole.DEVELOPER)
    if perm:
        return perm

    environments = _get_environments(request)

    if request.method == "POST":
        try:
            flag = FeatureFlagService.create_flag(
                name=request.POST.get("name", "").strip(),
                key=request.POST.get("key", "").strip(),
                environment=get_object_or_404(environments, pk=request.POST.get("environment_id")),
                created_by=request.user,
                flag_type=request.POST.get("flag_type", "boolean"),
                risk_level=request.POST.get("risk_level", "low"),
                description=request.POST.get("description", ""),
            )
            messages.success(request, f"Flag '{flag.key}' created successfully.")
            return redirect("dashboard_flag_detail", pk=flag.pk)
        except (ValidationError, Exception) as e:
            error_msg = e.message if hasattr(e, "message") else str(e)
            return render(request, "dashboard/flag_create.html", {
                "environments": environments,
                "error": error_msg,
            })

    return render(request, "dashboard/flag_create.html", {
        "environments": environments,
    })


# ---------------------------------------------------------------------------
# Flag Detail
# ---------------------------------------------------------------------------

@login_required
def flag_detail_view(request, pk):
    tenant = _get_tenant(request)
    flag = get_object_or_404(
        FeatureFlag.objects
        .filter(environment__tenant=tenant)
        .select_related("environment", "depends_on", "created_by", "approved_by")
        .prefetch_related("variants", "targeting_rules"),
        pk=pk,
    )

    targeting_rules = flag.targeting_rules.all().order_by("priority")

    audit_logs = (
        AuditLog.objects
        .filter(tenant=tenant, object_type="FeatureFlag", object_id=str(flag.id))
        .select_related("actor")
        .order_by("-timestamp")[:20]
    )

    return render(request, "dashboard/flag_detail.html", {
        "flag": flag,
        "targeting_rules": targeting_rules,
        "audit_logs": audit_logs,
        "environments": _get_environments(request),
    })


# ---------------------------------------------------------------------------
# Flag Actions (POST)
# ---------------------------------------------------------------------------

@require_POST
@login_required
def flag_toggle_view(request, pk):
    perm = _require_role(request, UserRole.DEVELOPER)
    if perm:
        return perm

    tenant = _get_tenant(request)
    flag = get_object_or_404(FeatureFlag, pk=pk, environment__tenant=tenant)

    is_enabled = request.POST.get("is_enabled", "false").lower() == "true"
    try:
        FeatureFlagService.toggle_flag(flag, is_enabled, request.user)
        messages.success(request, f"Flag '{flag.key}' {'enabled' if is_enabled else 'disabled'}.")
    except ValidationError as e:
        messages.error(request, e.message if hasattr(e, "message") else str(e))

    referer = request.META.get("HTTP_REFERER", "")
    if "flags/" in referer and str(pk) in referer:
        return redirect("dashboard_flag_detail", pk=pk)
    return redirect("dashboard_flags")


@require_POST
@login_required
def flag_archive_view(request, pk):
    perm = _require_role(request, UserRole.ADMIN)
    if perm:
        return perm

    tenant = _get_tenant(request)
    flag = get_object_or_404(FeatureFlag, pk=pk, environment__tenant=tenant)

    try:
        FeatureFlagService.archive_flag(flag)
        messages.success(request, f"Flag '{flag.key}' archived.")
    except ValidationError as e:
        messages.error(request, e.message if hasattr(e, "message") else str(e))

    return redirect("dashboard_flag_detail", pk=pk)


@require_POST
@login_required
def flag_kill_switch_view(request, pk):
    perm = _require_role(request, UserRole.ADMIN)
    if perm:
        return perm

    tenant = _get_tenant(request)
    flag = get_object_or_404(FeatureFlag, pk=pk, environment__tenant=tenant)

    action = request.POST.get("action", "activate")
    try:
        if action == "activate":
            FeatureFlagService.activate_kill_switch(flag)
            messages.success(request, f"Kill switch activated for '{flag.key}'.")
        else:
            FeatureFlagService.deactivate_kill_switch(flag)
            messages.success(request, f"Kill switch deactivated for '{flag.key}'.")
    except ValidationError as e:
        messages.error(request, e.message if hasattr(e, "message") else str(e))

    return redirect("dashboard_flag_detail", pk=pk)


# ---------------------------------------------------------------------------
# Variant Editor (POST)
# ---------------------------------------------------------------------------

@require_POST
@login_required
def flag_variants_view(request, pk):
    perm = _require_role(request, UserRole.DEVELOPER)
    if perm:
        return perm

    tenant = _get_tenant(request)
    flag = get_object_or_404(FeatureFlag, pk=pk, environment__tenant=tenant)

    try:
        count = int(request.POST.get("variant_count", 0))
        variants_data = []
        for i in range(count):
            name = request.POST.get(f"variants-{i}-name", "").strip()
            value = request.POST.get(f"variants-{i}-value", "").strip()
            pct = request.POST.get(f"variants-{i}-percentage", "0")
            is_ctrl = request.POST.get(f"variants-{i}-is_control", "") == "true"
            if name and value:
                variants_data.append({
                    "name": name,
                    "value": value,
                    "rollout_percentage": Decimal(pct),
                    "is_control": is_ctrl,
                })

        FlagVariantService.set_variants(flag, variants_data)
        messages.success(request, "Variants updated successfully.")
    except (ValidationError, Exception) as e:
        error_msg = e.message if hasattr(e, "message") else str(e)
        messages.error(request, f"Failed to update variants: {error_msg}")

    return redirect("dashboard_flag_detail", pk=pk)


# ---------------------------------------------------------------------------
# Targeting Rule Builder (POST + DELETE)
# ---------------------------------------------------------------------------

@require_POST
@login_required
def rule_create_view(request, flag_pk):
    perm = _require_role(request, UserRole.DEVELOPER)
    if perm:
        return perm

    tenant = _get_tenant(request)
    flag = get_object_or_404(FeatureFlag, pk=flag_pk, environment__tenant=tenant)

    try:
        value_raw = request.POST.get("value", "").strip()
        # Try to parse as JSON for list operators
        operator = request.POST.get("operator", "equals")
        if operator in ("in_list", "not_in_list"):
            try:
                value = json.loads(value_raw)
            except (json.JSONDecodeError, ValueError):
                value = [v.strip() for v in value_raw.split(",") if v.strip()]
        else:
            value = value_raw

        TargetingRule.objects.create(
            flag=flag,
            rule_type=request.POST.get("rule_type", "user_id"),
            operator=operator,
            value=value,
            attribute_key=request.POST.get("attribute_key", "").strip(),
            priority=int(request.POST.get("priority", 0)),
        )
        messages.success(request, "Targeting rule added.")
    except Exception as e:
        messages.error(request, f"Failed to add rule: {e}")

    # If HTMX request, return partial
    if request.headers.get("HX-Request"):
        rules = flag.targeting_rules.all().order_by("priority")
        return render(request, "partials/targeting_rules_list.html", {
            "targeting_rules": rules,
            "flag": flag,
            "user": request.user,
        })

    return redirect("dashboard_flag_detail", pk=flag_pk)


@require_POST
@login_required
def rule_delete_view(request, rule_pk):
    perm = _require_role(request, UserRole.DEVELOPER)
    if perm:
        return perm

    tenant = _get_tenant(request)
    rule = get_object_or_404(
        TargetingRule,
        pk=rule_pk,
        flag__environment__tenant=tenant,
    )
    flag = rule.flag
    rule.delete()
    messages.success(request, "Targeting rule deleted.")

    if request.headers.get("HX-Request"):
        rules = flag.targeting_rules.all().order_by("priority")
        return render(request, "partials/targeting_rules_list.html", {
            "targeting_rules": rules,
            "flag": flag,
            "user": request.user,
        })

    return redirect("dashboard_flag_detail", pk=flag.pk)


# ---------------------------------------------------------------------------
# Approval Queue
# ---------------------------------------------------------------------------

@login_required
def approval_queue_view(request):
    perm = _require_role(request, UserRole.ADMIN)
    if perm:
        return perm

    tenant = _get_tenant(request)
    selected_status = request.GET.get("status", "pending")

    qs = (
        ApprovalRequest.objects
        .filter(flag__environment__tenant=tenant)
        .select_related("flag", "flag__environment", "requested_by", "reviewed_by")
        .order_by("-created_at")
    )

    if selected_status and selected_status != "all":
        qs = qs.filter(status=selected_status)
    elif not selected_status:
        selected_status = "all"

    pending_count = ApprovalRequest.objects.filter(
        flag__environment__tenant=tenant,
        status=ApprovalStatus.PENDING,
    ).count()

    return render(request, "dashboard/approvals.html", {
        "approvals": qs[:50],
        "selected_status": selected_status,
        "pending_count": pending_count,
        "environments": _get_environments(request),
    })


@require_POST
@login_required
def approval_action_view(request, pk):
    perm = _require_role(request, UserRole.ADMIN)
    if perm:
        return perm

    tenant = _get_tenant(request)
    approval = get_object_or_404(
        ApprovalRequest.objects.select_related("flag", "flag__environment", "requested_by", "reviewed_by"),
        pk=pk,
        flag__environment__tenant=tenant,
    )

    action = request.POST.get("action", "")
    comment = request.POST.get("comment", "").strip()

    try:
        if action == "approve":
            ApprovalService.approve_request(approval, reviewer=request.user, comment=comment)
            messages.success(request, f"Approved: {approval.flag.key}")
        elif action == "reject":
            ApprovalService.reject_request(approval, reviewer=request.user, comment=comment)
            messages.success(request, f"Rejected: {approval.flag.key}")
    except ValidationError as e:
        messages.error(request, e.message if hasattr(e, "message") else str(e))

    # If HTMX, return updated card
    if request.headers.get("HX-Request"):
        approval.refresh_from_db()
        return render(request, "partials/approval_card.html", {
            "approval": approval,
            "user": request.user,
        })

    return redirect("dashboard_approvals")


@require_POST
@login_required
def request_approval_view(request, flag_pk):
    perm = _require_role(request, UserRole.DEVELOPER)
    if perm:
        return perm

    tenant = _get_tenant(request)
    flag = get_object_or_404(FeatureFlag, pk=flag_pk, environment__tenant=tenant)

    try:
        ApprovalService.create_approval_request(
            flag=flag,
            requested_by=request.user,
            change_description=request.POST.get("change_description", "").strip(),
        )
        messages.success(request, "Approval request submitted.")
    except ValidationError as e:
        messages.error(request, e.message if hasattr(e, "message") else str(e))

    return redirect("dashboard_flag_detail", pk=flag_pk)


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

@login_required
def audit_log_view(request):
    perm = _require_role(request, UserRole.ADMIN)
    if perm:
        return perm

    tenant = _get_tenant(request)
    qs = (
        AuditLog.objects
        .filter(tenant=tenant)
        .select_related("actor")
        .order_by("-timestamp")
    )

    # Filters
    action = request.GET.get("action", "")
    obj_type = request.GET.get("object_type", "")
    actor = request.GET.get("actor", "").strip()
    obj_id = request.GET.get("object_id", "").strip()

    if action:
        qs = qs.filter(action=action)
    if obj_type:
        qs = qs.filter(object_type=obj_type)
    if actor:
        qs = qs.filter(actor__email__icontains=actor)
    if obj_id:
        qs = qs.filter(object_id=obj_id)

    return render(request, "dashboard/audit_logs.html", {
        "logs": qs[:100],
        "environments": _get_environments(request),
    })


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@login_required
def analytics_view(request):
    tenant = _get_tenant(request)
    if not tenant:
        return render(request, "dashboard/analytics.html", {"analytics": {}})

    seven_days_ago = timezone.now() - timedelta(days=7)

    events = EvaluationEvent.objects.filter(
        flag__environment__tenant=tenant,
        timestamp__gte=seven_days_ago,
    )

    total_evaluations = events.count()
    unique_users = events.values("user_identifier").distinct().count()
    unique_flags = events.values("flag_key").distinct().count()

    top_flags = list(
        events
        .values("flag_key")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # Variant distribution for top 5 flags
    variant_distribution = []
    for item in top_flags[:5]:
        flag_events = events.filter(flag_key=item["flag_key"])
        total = flag_events.count() or 1
        variants_qs = (
            flag_events
            .values("evaluated_variant")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        variants = []
        for v in variants_qs:
            val = v["evaluated_variant"]
            if isinstance(val, dict):
                val = json.dumps(val)
            elif val is None:
                val = "null"
            else:
                val = str(val)
            variants.append({
                "value": val,
                "count": v["count"],
                "pct": round(v["count"] / total * 100, 1),
            })
        variant_distribution.append({
            "flag_key": item["flag_key"],
            "variants": variants,
        })

    # Daily evaluations
    daily_evaluations = list(
        events
        .annotate(date=TruncDate("timestamp"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )
    max_daily = max((d["count"] for d in daily_evaluations), default=0)

    return render(request, "dashboard/analytics.html", {
        "analytics": {
            "total_evaluations": total_evaluations,
            "unique_users": unique_users,
            "unique_flags": unique_flags,
            "top_flags": top_flags,
            "variant_distribution": variant_distribution,
            "daily_evaluations": daily_evaluations,
            "max_daily": max_daily,
        },
        "environments": _get_environments(request),
    })
