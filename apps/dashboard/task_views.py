from datetime import date
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import Invitation, UserRole
from apps.audit.models import ActivityEntry, AuditLog
from apps.notifications.models import Notification
from apps.projects.models import Project, ProjectMember
from apps.tasks.models import Task, TaskStatus
from apps.tasks.services import TaskWorkflowService
from apps.time_tracking.models import TimeEntry
from apps.time_tracking.services import TimeEntryService

User = get_user_model()


def _org(request):
    return getattr(request.user, "organization", None)


@login_required
def dashboard_home(request):
    return redirect("dashboard_projects")


@login_required
def audit_view(request):
    org = _org(request)
    if not org:
        return render(request, "dashboard/audit.html", {"logs": []})

    logs = (
        AuditLog.objects
        .filter(organization=org)
        .select_related("actor")
        .order_by("-timestamp")
    )[:200]

    return render(request, "dashboard/audit.html", {"logs": logs})


@login_required
def performance_view(request):
    org = _org(request)
    if not org:
        return render(
            request,
            "dashboard/performance.html",
            {"metrics": {"hours_30d": 0, "completed_30d": 0, "overdue_open": 0, "top_members": []}},
        )

    since = timezone.now().date() - timedelta(days=30)

    hours_30d = (
        TimeEntry.objects
        .filter(user__organization=org, date__gte=since)
        .aggregate(total=Sum("hours"))
        .get("total")
        or 0
    )

    completed_30d = (
        Task.objects
        .filter(project__organization=org, status=TaskStatus.COMPLETED, completed_at__isnull=False, completed_at__date__gte=since)
        .count()
    )

    overdue_open = (
        Task.objects
        .filter(project__organization=org, is_overdue=True)
        .exclude(status=TaskStatus.COMPLETED)
        .count()
    )

    top_members_qs = (
        TimeEntry.objects
        .filter(user__organization=org, date__gte=since)
        .values("user__email")
        .annotate(hours=Sum("hours"))
        .order_by("-hours", "user__email")
    )[:10]

    top_members = [
        {"email": row["user__email"], "hours": row["hours"] or 0}
        for row in top_members_qs
    ]

    metrics = {
        "hours_30d": hours_30d,
        "completed_30d": completed_30d,
        "overdue_open": overdue_open,
        "top_members": top_members,
    }

    return render(request, "dashboard/performance.html", {"metrics": metrics})


@login_required
def analytics_view(request):
    org = _org(request)
    if not org:
        return render(
            request,
            "dashboard/analytics.html",
            {"analytics": {"completed_7d": 0, "hours_7d": 0, "overdue_open": 0, "by_status": []}},
        )

    since = timezone.now().date() - timedelta(days=7)

    completed_7d = (
        Task.objects
        .filter(project__organization=org, status=TaskStatus.COMPLETED, completed_at__isnull=False, completed_at__date__gte=since)
        .count()
    )

    hours_7d = (
        TimeEntry.objects
        .filter(user__organization=org, date__gte=since)
        .aggregate(total=Sum("hours"))
        .get("total")
        or 0
    )

    overdue_open = (
        Task.objects
        .filter(project__organization=org, is_overdue=True)
        .exclude(status=TaskStatus.COMPLETED)
        .count()
    )

    status_counts = (
        Task.objects
        .filter(project__organization=org)
        .values("status")
        .annotate(count=Count("id"))
    )
    counts_by_status = {row["status"]: row["count"] for row in status_counts}
    by_status: list[dict[str, object]] = [
        {"key": key, "label": label, "count": counts_by_status.get(key, 0)}
        for key, label in TaskStatus.choices
    ]

    analytics = {
        "completed_7d": completed_7d,
        "hours_7d": hours_7d,
        "overdue_open": overdue_open,
        "by_status": by_status,
    }

    return render(request, "dashboard/analytics.html", {"analytics": analytics})


@login_required
def project_list_view(request):
    org = _org(request)
    if not org:
        return render(request, "dashboard/projects.html", {"projects": []})

    projects = (
        Project.objects
        .filter(organization=org, memberships__user=request.user)
        .select_related("created_by")
        .distinct()
        .order_by("name")
    )
    return render(request, "dashboard/projects.html", {"projects": projects})


@login_required
def project_create_view(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip()
        if not name:
            messages.error(request, "Project name is required.")
            return redirect("dashboard_projects")

        try:
            project = Project.objects.create(
                organization=_org(request),
                name=name,
                description=description,
                created_by=request.user,
            )
            ProjectMember.objects.get_or_create(project=project, user=request.user)
            messages.success(request, "Project created.")
            return redirect("dashboard_project_detail", pk=project.pk)
        except Exception:
            messages.error(request, "Failed to create project.")
            return redirect("dashboard_projects")

    return redirect("dashboard_projects")


@login_required
def project_detail_view(request, pk: int):
    org = _org(request)
    project = get_object_or_404(
        Project.objects.filter(organization=org, memberships__user=request.user).distinct(),
        pk=pk,
    )

    memberships = (
        ProjectMember.objects
        .filter(project=project)
        .select_related("user")
        .order_by("user__email")
    )

    tasks = (
        Task.objects
        .filter(project=project)
        .select_related("assignee", "reviewer", "created_by")
        .order_by("-updated_at")
    )

    by_status: dict[str, list[Task]] = {status: [] for status, _ in TaskStatus.choices}
    for t in tasks:
        by_status[t.status].append(t)

    columns = [
        {"key": key, "label": label, "tasks": by_status.get(key, [])}
        for key, label in TaskStatus.choices
    ]

    return render(
        request,
        "dashboard/project_detail.html",
        {
            "project": project,
            "memberships": memberships,
            "columns": columns,
            "statuses": TaskStatus.choices,
        },
    )


@require_POST
@login_required
def project_add_member_view(request, pk: int):
    project = get_object_or_404(
        Project.objects.filter(organization=_org(request), memberships__user=request.user).distinct(),
        pk=pk,
    )

    if request.user.role not in (UserRole.OWNER, UserRole.PROJECT_MANAGER):
        messages.error(request, "Insufficient permissions.")
        return redirect("dashboard_project_detail", pk=pk)

    email = (request.POST.get("email") or "").strip().lower()
    if not email:
        messages.error(request, "Email is required.")
        return redirect("dashboard_project_detail", pk=pk)

    user = User.objects.filter(email=email, organization=request.user.organization).first()
    if not user:
        messages.error(request, "User not found in your organization.")
        return redirect("dashboard_project_detail", pk=pk)

    ProjectMember.objects.get_or_create(project=project, user=user)
    messages.success(request, "Member added.")
    return redirect("dashboard_project_detail", pk=pk)


@require_POST
@login_required
def project_remove_member_view(request, pk: int, member_id: int):
    project = get_object_or_404(
        Project.objects.filter(organization=_org(request), memberships__user=request.user).distinct(),
        pk=pk,
    )

    if request.user.role not in (UserRole.OWNER, UserRole.PROJECT_MANAGER):
        messages.error(request, "Insufficient permissions.")
        return redirect("dashboard_project_detail", pk=pk)

    membership = get_object_or_404(ProjectMember, pk=member_id, project=project)
    if membership.user_id == request.user.id:
        messages.error(request, "You cannot remove yourself.")
        return redirect("dashboard_project_detail", pk=pk)

    membership.delete()
    messages.success(request, "Member removed.")
    return redirect("dashboard_project_detail", pk=pk)


@require_POST
@login_required
def task_create_view(request, project_pk: int):
    project = get_object_or_404(
        Project.objects.filter(organization=_org(request), memberships__user=request.user).distinct(),
        pk=project_pk,
    )

    title = (request.POST.get("title") or "").strip()
    if not title:
        messages.error(request, "Task title is required.")
        return redirect("dashboard_project_detail", pk=project_pk)

    description = (request.POST.get("description") or "").strip()
    priority = request.POST.get("priority") or "medium"

    assignee_id = request.POST.get("assignee") or None
    reviewer_id = request.POST.get("reviewer") or None

    assignee = None
    reviewer = None
    if assignee_id:
        assignee = User.objects.filter(pk=assignee_id, organization=request.user.organization).first()
    if reviewer_id:
        reviewer = User.objects.filter(pk=reviewer_id, organization=request.user.organization).first()

    Task.objects.create(
        project=project,
        title=title,
        description=description,
        priority=priority,
        assignee=assignee,
        reviewer=reviewer,
        created_by=request.user,
    )
    messages.success(request, "Task created.")
    return redirect("dashboard_project_detail", pk=project_pk)


@login_required
def task_detail_view(request, pk: int):
    task = get_object_or_404(
        Task.objects.filter(project__organization=_org(request), project__memberships__user=request.user).distinct(),
        pk=pk,
    )

    time_entries = task.time_entries.select_related("user").order_by("-created_at")[:50]

    return render(
        request,
        "dashboard/task_detail.html",
        {
            "task": task,
            "statuses": TaskStatus.choices,
            "time_entries": time_entries,
        },
    )


@require_POST
@login_required
def task_transition_view(request, pk: int):
    task = get_object_or_404(
        Task.objects.filter(project__organization=_org(request), project__memberships__user=request.user).distinct(),
        pk=pk,
    )
    to_status = request.POST.get("to_status")
    if not to_status:
        messages.error(request, "Missing status.")
        return redirect("dashboard_task_detail", pk=pk)

    try:
        TaskWorkflowService.transition(task=task, actor=request.user, to_status=to_status)
        messages.success(request, "Task updated.")
    except ValidationError as e:
        msg = e.message if hasattr(e, "message") else str(e)
        messages.error(request, msg)

    return redirect("dashboard_task_detail", pk=pk)


@require_POST
@login_required
def time_entry_create_view(request, task_pk: int):
    task = get_object_or_404(
        Task.objects.filter(project__organization=_org(request), project__memberships__user=request.user).distinct(),
        pk=task_pk,
    )

    hours_raw = request.POST.get("hours")
    date_raw = request.POST.get("date")

    try:
        hours = Decimal(str(hours_raw))
        entry_date = date.fromisoformat(str(date_raw))
        TimeEntryService.create_time_entry(
            user=request.user,
            task=task,
            hours=hours,
            date=entry_date,
        )
        messages.success(request, "Time logged.")
        return redirect("dashboard_task_detail", pk=task_pk)
    except Exception:
        messages.error(request, "Failed to log time.")
        return redirect("dashboard_task_detail", pk=task_pk)


# ---------------------------------------------------------------------------
# Invitation views
# ---------------------------------------------------------------------------


@login_required
def invitation_list_view(request):
    org = _org(request)
    if not org:
        return render(request, "dashboard/invitations.html", {"invitations": []})

    invitations = (
        Invitation.objects
        .filter(organization=org)
        .order_by("-created_at")
    )[:100]

    return render(request, "dashboard/invitations.html", {"invitations": invitations})


@require_POST
@login_required
def invitation_create_view(request):
    org = _org(request)
    if request.user.role not in (UserRole.OWNER, UserRole.PROJECT_MANAGER):
        messages.error(request, "Only owners and project managers can send invitations.")
        return redirect("dashboard_invitations")

    email = (request.POST.get("email") or "").strip().lower()
    role = request.POST.get("role") or "developer"

    if not email:
        messages.error(request, "Email is required.")
        return redirect("dashboard_invitations")

    if User.objects.filter(email=email, organization=org).exists():
        messages.error(request, "This user is already in your organization.")
        return redirect("dashboard_invitations")

    if Invitation.objects.filter(email=email, organization=org, used_at__isnull=True).exists():
        messages.error(request, "An active invitation already exists for this email.")
        return redirect("dashboard_invitations")

    import secrets
    Invitation.objects.create(
        email=email,
        role=role,
        organization=org,
        created_by=request.user,
        token=secrets.token_urlsafe(32),
        expires_at=timezone.now() + timedelta(hours=48),
    )
    messages.success(request, f"Invitation sent to {email}.")
    return redirect("dashboard_invitations")


# ---------------------------------------------------------------------------
# Notification views
# ---------------------------------------------------------------------------


@login_required
def notification_list_view(request):
    org = _org(request)
    if not org:
        return render(request, "dashboard/notifications.html", {"notifications": []})

    notifications = (
        Notification.objects
        .filter(recipient=request.user, organization=org)
        .order_by("-created_at")
    )[:100]

    return render(request, "dashboard/notifications.html", {"notifications": notifications})


@require_POST
@login_required
def notification_mark_read_view(request, pk: int):
    notif = get_object_or_404(
        Notification, pk=pk, recipient=request.user, organization=_org(request)
    )
    notif.is_read = True
    notif.save(update_fields=["is_read"])
    messages.success(request, "Notification marked as read.")
    return redirect("dashboard_notifications")


@require_POST
@login_required
def notifications_mark_all_read_view(request):
    org = _org(request)
    if org:
        Notification.objects.filter(
            recipient=request.user, organization=org, is_read=False
        ).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("dashboard_notifications")


# ---------------------------------------------------------------------------
# Activity Feed view
# ---------------------------------------------------------------------------


@login_required
def activity_feed_view(request):
    org = _org(request)
    if not org:
        return render(request, "dashboard/activity.html", {"activities": []})

    activities = (
        ActivityEntry.objects
        .filter(organization=org)
        .select_related("actor", "task")
        .order_by("-created_at")
    )[:200]

    return render(request, "dashboard/activity.html", {"activities": activities})
