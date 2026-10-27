"""Execute one contract observation against the original upstream Python code."""
from __future__ import annotations
import calendar
import io
import json
import logging
import struct
import sys
import traceback
from datetime import datetime, date, timedelta
from pathlib import Path
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

def run(case: str, source: Path, params: dict):
    sys.path[:0] = [str(source / "src"), str(source)]
    if case.startswith("C"):
        from django.conf import settings
        settings.configure(
            SECRET_KEY="public-fixture-signing-key", USE_TZ=True, ALLOWED_HOSTS=["testserver"],
            CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
            INSTALLED_APPS=["django.contrib.auth", "django.contrib.contenttypes"],
            SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies",
            SESSION_SAVE_EVERY_REQUEST=True,
            DJANGO_GRAPHEX={"CACHE_ACTIVE": True, "CACHE_TIMEOUT": 60})
        import django
        django.setup()
        from django.core.cache import cache
        from django.http import HttpResponse
        from django.test import RequestFactory
        from django.middleware.cache import CacheMiddleware, UpdateCacheMiddleware, FetchFromCacheMiddleware
        from django.utils.cache import patch_vary_headers
        cache.clear()
        factory = RequestFactory()
        calls = 0
        if case == "C5":
            import graphene
            from types import SimpleNamespace
            from django.contrib.auth.models import AnonymousUser
            from django_graphex.views import GraphQLView
            class Query(graphene.ObjectType):
                me = graphene.String()
                def resolve_me(root, info):
                    nonlocal calls
                    calls += 1
                    return info.context.user.username if info.context.user.is_authenticated else "anon"
            view = GraphQLView.as_view(schema=graphene.Schema(query=Query))
            observed = []
            for actor in params["actors"]:
                request = factory.post("/graphql/", json.dumps({"query": "{ me }"}), content_type="application/json")
                request.user = AnonymousUser() if actor == "anon" else SimpleNamespace(
                    is_authenticated=True, pk=actor, id=actor, username=actor)
                response = view(request)
                observed.append({"status": response.status_code, "body": json.loads(response.content).get("data", {}).get("me")})
            return {"responses": observed, "origin_calls": calls}
        if case == "C6":
            from django.contrib.sessions.middleware import SessionMiddleware
            from django.contrib.sessions.backends.signed_cookies import SessionStore
            store = SessionStore()
            store["identity"] = params.get("owner", "alice")
            store.save()
            session_cookie = store.session_key
            def view(request):
                nonlocal calls
                calls += 1
                if params.get("touch_session"):
                    request.session.get("identity")
                return HttpResponse("public")
            chain = UpdateCacheMiddleware(SessionMiddleware(FetchFromCacheMiddleware(view)))
            responses = []
            for actor in (["anon", "anon"] if params.get("empty") else ["owner", "anon"]):
                request = factory.get("/paper-session/")
                if actor == "owner":
                    request.COOKIES[settings.SESSION_COOKIE_NAME] = session_cookie
                    request.META["HTTP_COOKIE"] = settings.SESSION_COOKIE_NAME + "=" + session_cookie
                response = chain(request)
                responses.append({"body": response.content.decode(), "cookie": response.cookies.get(settings.SESSION_COOKIE_NAME).value if settings.SESSION_COOKIE_NAME in response.cookies else None})
            first_cookie=responses[0]["cookie"]
            owner_preserved=SessionStore(session_key=first_cookie).load().get("identity")==params.get("owner","alice") if first_cookie else False
            return {"responses": responses, "origin_calls": calls, "owner_preserved":owner_preserved}
        def view(request):
            nonlocal calls
            calls += 1
            if case == "C3":
                body = "public" if params.get("public") else request.headers.get("Authorization", "anon")
            elif case == "C4":
                body = "public"
            else:
                body = "public" if params.get("public") else request.COOKIES.get("actor", "anon")
            response = HttpResponse(body)
            response["Cache-Control"] = params.get("directive", "public, max-age=300" if params.get("public") else "max-age=300")
            if case == "C4" and not params.get("public"):
                response.set_cookie("session", "created-" + str(calls))
                patch_vary_headers(response, ("Cookie",))
            if params.get("vary_language"):
                patch_vary_headers(response, ("Accept-Language",))
            return response
        chain = CacheMiddleware(view)
        responses = []
        for actor in params.get("actors", ["alice", "bob"]):
            request = factory.get("/paper-contract/")
            if case == "C3" and actor != "anon":
                request.META["HTTP_AUTHORIZATION"] = actor
            if case == "C4" and not params.get("no_cookie"):
                request.COOKIES[params.get("cookie_name", "theme")] = "same"
                request.META["HTTP_COOKIE"] = params.get("cookie_name", "theme") + "=same"
                if params.get("existing_session"):
                    request.COOKIES["session"] = "old"
                    request.META["HTTP_COOKIE"] = "session=old"
            if case == "C8":
                request.COOKIES["actor"] = actor
                request.META["HTTP_COOKIE"] = "actor=" + actor
            response = chain(request)
            responses.append({"body": response.content.decode(),
                              "cookie": response.cookies["session"].value if "session" in response.cookies else None,
                              "vary": response.get("Vary", ""), "cache_control":response.get("Cache-Control","")})
        return {"responses": responses, "origin_calls": calls}
    if case == "T1":
        import arrow
        start = arrow.get(params["start"])
        values = list(arrow.Arrow.range(params.get("frame", "month"), start, limit=params.get("count", 4)))
        return [value.format("YYYY-MM-DD") for value in values]
    if case == "T2":
        from croniter import croniter
        start = datetime.fromisoformat(params["start"])
        if params.get("zone"):
            start = start.replace(tzinfo=ZoneInfo(params["zone"]))
        iterator = croniter(params["expression"], start, expand_from_start_time=True)
        return iterator.expanded[params.get("field", 1)]
    if case == "T3":
        from dateutil import tz
        header = b"TZif3" + bytes(15) + struct.pack(">6l", 0, 0, 0, 0, 0, 0)
        zone = tz.tzfile(io.BytesIO(header + header + b"\n" + params["rule"].encode() + b"\n"))
        return [datetime.fromisoformat(value).replace(tzinfo=zone).tzname() for value in params["dates"]]
    if case in {"T4", "T5"}:
        import pendulum
        if case == "T4":
            calendar.setfirstweekday(params["firstweekday"])
            original = calendar.firstweekday()
            cls = pendulum.DateTime if params.get("datetime") else pendulum.Date
            value = cls(*params["date"])
            result = value.nth_of("month", params["n"], params.get("weekday",0)) if params.get("method")=="nth_of" else getattr(value, params.get("method", "first_of"))("month", params.get("weekday", 0))
            return {"date": result.strftime("%Y-%m-%d"), "global_unchanged": calendar.firstweekday() == original}
        value = pendulum.datetime(*params["date"], tz=params["zone"])
        output = value + pendulum.duration(**params["duration"])
        return {"wall": output.strftime("%Y-%m-%d %H:%M"), "elapsed": int(output.timestamp() - value.timestamp())}
    if case == "TD2":
        from apscheduler.triggers.cron import CronTrigger
        start=datetime.fromisoformat(params["start"]).replace(tzinfo=ZoneInfo(params["zone"]))
        trigger=CronTrigger(hour=2,minute=30,start_time=start,timezone=start.tzinfo)
        return trigger.next().strftime("%Y-%m-%d %H:%M")
    if case == "T6":
        import apscheduler.schedulers.base as base
        from apscheduler.schedulers.base import BaseScheduler
        from apscheduler.jobstores.base import BaseJobStore
        start = datetime.fromisoformat(params["start"]).replace(tzinfo=ZoneInfo(params["zone"]), fold=params.get("start_fold", 0))
        target = datetime.fromisoformat(params["end"]).replace(tzinfo=start.tzinfo, fold=params.get("end_fold", 0))
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return start.astimezone(tz) if tz else start
        class Scheduler(BaseScheduler):
            def wakeup(self):
                pass
            def shutdown(self, wait=True):
                pass
        store = MagicMock(BaseJobStore)
        store.get_due_jobs.return_value = []
        store.get_next_run_time.return_value = target
        scheduler = Scheduler(jobstores={"default": store}, timezone=start.tzinfo)
        base.datetime = FixedDateTime
        logging.disable(logging.CRITICAL)
        return scheduler._process_jobs()
    raise ValueError("Unsupported Python case: " + case)

if __name__ == "__main__":
    specification = json.loads(sys.stdin.read())
    try:
        observed = run(specification["case"], Path(specification["source"]), specification["params"])
        print(json.dumps({"execution": "VALID", "observed": observed}, allow_nan=False))
    except (ImportError, ModuleNotFoundError) as error:
        print(json.dumps({"execution": "INFRA_ERROR", "error_type": type(error).__name__, "error": str(error)}))
    except Exception as error:
        print(json.dumps({"execution": "PRODUCT_EXCEPTION", "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc(limit=4)}))
