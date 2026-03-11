from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.views import View

from .forms import RegisterForm, LoginForm

User = get_user_model()


class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("chat:lobby")
        return render(request, "accounts/register.html", {"form": RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Send verification email
            self._send_verification_email(user)
            messages.success(
                request,
                "Account created! Check your email for a verification link.",
            )
            return redirect("accounts:login")
        return render(request, "accounts/register.html", {"form": form})

    def _send_verification_email(self, user):
        verification_url = (
            f"{settings.SITE_URL}/accounts/verify/{user.email_verification_token}/"
        )
        try:
            send_mail(
                subject="Verify your Antigravity account",
                message=(
                    f"Welcome to Antigravity!\n\n"
                    f"Click the link below to verify your email:\n"
                    f"{verification_url}\n\n"
                    f"If you didn't create this account, ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass  # Don't break registration if email fails


class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("chat:lobby")
        return render(request, "accounts/login.html", {"form": LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()
            password = form.cleaned_data["password"]
            user = authenticate(request, username=email, password=password)
            if user is not None:
                if user.is_banned:
                    messages.error(request, "Your account has been suspended.")
                    return render(request, "accounts/login.html", {"form": form})
                if not user.is_email_verified:
                    messages.warning(
                        request,
                        "Please verify your email first. Check your inbox.",
                    )
                    return render(request, "accounts/login.html", {"form": form})
                login(request, user)
                return redirect("chat:lobby")
            else:
                messages.error(request, "Invalid email or password.")
        return render(request, "accounts/login.html", {"form": form})


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("landing")

    def post(self, request):
        logout(request)
        return redirect("landing")


class VerifyEmailView(View):
    def get(self, request, token):
        try:
            user = User.objects.get(email_verification_token=token)
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
            messages.success(request, "Email verified! You can now log in.")
        except User.DoesNotExist:
            messages.error(request, "Invalid or expired verification link.")
        return redirect("accounts:login")
