import pytest
from django.core.exceptions import ValidationError

from apps.tasks.models import Task, TaskDependency, TaskStatus
from apps.tasks.services import DependencyService, TaskWorkflowService


@pytest.mark.django_db
class TestDependencyCreation:
    def test_add_dependency(self, project_with_team, owner_user):
        task_a = Task.objects.create(project=project_with_team, title="A", created_by=owner_user)
        task_b = Task.objects.create(project=project_with_team, title="B", created_by=owner_user)

        dep = DependencyService.add_dependency(task=task_b, depends_on=task_a, actor=owner_user)
        assert dep.task_id == task_b.id
        assert dep.depends_on_id == task_a.id

    def test_self_dependency_rejected(self, project_with_team, owner_user):
        task = Task.objects.create(project=project_with_team, title="Self", created_by=owner_user)
        with pytest.raises(ValidationError, match="cannot depend on itself"):
            DependencyService.add_dependency(task=task, depends_on=task, actor=owner_user)

    def test_duplicate_dependency_rejected(self, project_with_team, owner_user):
        task_a = Task.objects.create(project=project_with_team, title="A", created_by=owner_user)
        task_b = Task.objects.create(project=project_with_team, title="B", created_by=owner_user)
        DependencyService.add_dependency(task=task_b, depends_on=task_a, actor=owner_user)
        with pytest.raises(ValidationError, match="already exists"):
            DependencyService.add_dependency(task=task_b, depends_on=task_a, actor=owner_user)

    def test_remove_dependency(self, project_with_team, owner_user):
        task_a = Task.objects.create(project=project_with_team, title="A", created_by=owner_user)
        task_b = Task.objects.create(project=project_with_team, title="B", created_by=owner_user)
        DependencyService.add_dependency(task=task_b, depends_on=task_a, actor=owner_user)
        DependencyService.remove_dependency(task=task_b, depends_on=task_a, actor=owner_user)
        assert TaskDependency.objects.count() == 0


@pytest.mark.django_db
class TestCircularDependency:
    def test_direct_circular_rejected(self, project_with_team, owner_user):
        task_a = Task.objects.create(project=project_with_team, title="A", created_by=owner_user)
        task_b = Task.objects.create(project=project_with_team, title="B", created_by=owner_user)
        DependencyService.add_dependency(task=task_b, depends_on=task_a, actor=owner_user)
        with pytest.raises(ValidationError, match="circular"):
            DependencyService.add_dependency(task=task_a, depends_on=task_b, actor=owner_user)

    def test_indirect_circular_rejected(self, project_with_team, owner_user):
        task_a = Task.objects.create(project=project_with_team, title="A", created_by=owner_user)
        task_b = Task.objects.create(project=project_with_team, title="B", created_by=owner_user)
        task_c = Task.objects.create(project=project_with_team, title="C", created_by=owner_user)
        DependencyService.add_dependency(task=task_b, depends_on=task_a, actor=owner_user)
        DependencyService.add_dependency(task=task_c, depends_on=task_b, actor=owner_user)
        with pytest.raises(ValidationError, match="circular"):
            DependencyService.add_dependency(task=task_a, depends_on=task_c, actor=owner_user)


@pytest.mark.django_db
class TestDependencyEnforcement:
    def test_cannot_start_with_incomplete_dependency(self, project_with_team, owner_user, developer_user):
        task_a = Task.objects.create(project=project_with_team, title="Blocker", created_by=owner_user)
        task_b = Task.objects.create(
            project=project_with_team, title="Blocked", assignee=developer_user, created_by=owner_user,
        )
        DependencyService.add_dependency(task=task_b, depends_on=task_a, actor=owner_user)

        with pytest.raises(ValidationError, match="dependencies are not completed"):
            TaskWorkflowService.transition(task=task_b, actor=developer_user, to_status=TaskStatus.IN_PROGRESS)

    def test_can_start_when_dependency_completed(self, project_with_team, owner_user, developer_user, reviewer_user):
        task_a = Task.objects.create(
            project=project_with_team, title="Blocker", assignee=developer_user,
            reviewer=reviewer_user, created_by=owner_user,
        )
        task_b = Task.objects.create(
            project=project_with_team, title="Blocked", assignee=developer_user, created_by=owner_user,
        )
        DependencyService.add_dependency(task=task_b, depends_on=task_a, actor=owner_user)

        # Complete task_a through full workflow
        TaskWorkflowService.transition(task=task_a, actor=developer_user, to_status=TaskStatus.IN_PROGRESS)
        TaskWorkflowService.transition(task=task_a, actor=owner_user, to_status=TaskStatus.IN_REVIEW)
        TaskWorkflowService.transition(task=task_a, actor=reviewer_user, to_status=TaskStatus.APPROVED)
        TaskWorkflowService.transition(task=task_a, actor=owner_user, to_status=TaskStatus.COMPLETED)

        # Now task_b can start
        result = TaskWorkflowService.transition(task=task_b, actor=developer_user, to_status=TaskStatus.IN_PROGRESS)
        assert result.task.status == TaskStatus.IN_PROGRESS

    def test_cross_project_dependency_rejected(self, organization, owner_user):
        from apps.projects.models import Project, ProjectMember

        project_a = Project.objects.create(organization=organization, name="P-A", created_by=owner_user)
        project_b = Project.objects.create(organization=organization, name="P-B", created_by=owner_user)
        ProjectMember.objects.create(project=project_a, user=owner_user)
        ProjectMember.objects.create(project=project_b, user=owner_user)

        task_a = Task.objects.create(project=project_a, title="A", created_by=owner_user)
        task_b = Task.objects.create(project=project_b, title="B", created_by=owner_user)

        with pytest.raises(ValidationError, match="same project"):
            DependencyService.add_dependency(task=task_b, depends_on=task_a, actor=owner_user)
