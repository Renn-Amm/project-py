from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST


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
            next_url = (
                request.POST.get("next") or request.GET.get("next") or "dashboard_home"
            )
            return redirect(next_url)
        return render(request, "dashboard/login.html", {"form": {"errors": True}})
    return render(
        request, "dashboard/login.html", {"next": request.GET.get("next", "")}
    )


@require_POST
@login_required
def logout_view(request):
    logout(request)
    return redirect("dashboard_login")
