"""
Project-level access control for supervisors.

A Supervisor with is_admin=True sees/manages every project (legacy
behavior, preserved for accounts that existed before per-project scoping
was introduced). A non-admin supervisor is restricted to the projects
explicitly assigned to them via Supervisor.projects.
"""
from supervisor.models.project import Project


def accessible_projects(user):
    """Return the queryset of Project rows this supervisor may see/manage."""
    supervisor = getattr(user, 'supervisor', None)
    if supervisor is None:
        return Project.objects.none()
    if supervisor.is_admin:
        return Project.objects.all()
    return supervisor.projects.all()


def can_access_project(user, project):
    """True if this supervisor may see/manage the given Project instance."""
    supervisor = getattr(user, 'supervisor', None)
    if supervisor is None or project is None:
        return False
    if supervisor.is_admin:
        return True
    return supervisor.projects.filter(pk=project.pk).exists()
