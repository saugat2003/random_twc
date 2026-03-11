from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Create a password",
            "autocomplete": "new-password",
        }),
        min_length=8,
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Confirm password",
            "autocomplete": "new-password",
        }),
        label="Confirm Password",
    )

    class Meta:
        model = User
        fields = ["email"]
        widgets = {
            "email": forms.EmailInput(attrs={
                "class": "form-input",
                "placeholder": "your.name@college.edu",
                "autocomplete": "email",
            }),
        }

    def clean_email(self):
        from django.conf import settings
        email = self.cleaned_data["email"].lower().strip()
        domain = settings.ALLOWED_EMAIL_DOMAIN
        if domain and not email.endswith(f"@{domain}"):
            raise forms.ValidationError(
                f"Only @{domain} email addresses are allowed."
            )
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        pw2 = cleaned.get("password_confirm")
        if pw and pw2 and pw != pw2:
            self.add_error("password_confirm", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email.split("@")[0]  # auto-generate username
        # Ensure unique username
        base_username = user.username
        counter = 1
        while User.objects.filter(username=user.username).exists():
            user.username = f"{base_username}{counter}"
            counter += 1
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-input",
            "placeholder": "your.name@college.edu",
            "autocomplete": "email",
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Your password",
            "autocomplete": "current-password",
        }),
    )
