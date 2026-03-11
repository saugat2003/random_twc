from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import Report


@login_required
@require_POST
def submit_report(request):
    """Submit a report via AJAX."""
    import json

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    reason = data.get("reason", "")
    description = data.get("description", "")
    session_id = data.get("session_id", "")

    if reason not in dict(Report.REASON_CHOICES):
        return JsonResponse({"error": "Invalid reason"}, status=400)

    report = Report.objects.create(
        reporter=request.user,
        reason=reason,
        description=description,
    )

    # Link session if provided
    if session_id:
        from chat.models import ChatSession
        try:
            session = ChatSession.objects.get(id=session_id)
            report.reported_session = session
            report.save(update_fields=["reported_session"])
        except ChatSession.DoesNotExist:
            pass

    return JsonResponse({"success": True, "report_id": str(report.id)})
