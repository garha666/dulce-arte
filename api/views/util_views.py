"""Vistas utilitarias: health check, login y logout."""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render

from ..roles import rol_de


def health(request):
    """Sonda de salud para Nginx/systemd y monitoreo básico."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse(
            {"status": "error", "database": "unavailable"}, status=503
        )
    return JsonResponse(
        {"status": "ok", "service": "dulce-arte", "database": "ok"}
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            destino = request.GET.get("next") or (
                "tienda" if rol_de(user) == "cliente" else "home"
            )
            return redirect(destino)
        messages.error(request, "Usuario o contraseña incorrectos.")
    return render(request, "login.html")


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect("login")
