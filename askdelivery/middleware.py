# -*- coding: utf-8 -*-

import re
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

from .settings import LOGIN_NOT_REQUIRED

from threading import local
from core.models import User, Usuario


class LoginRequiredMiddleware(MiddlewareMixin):

    def __init__(self, get_response=None, *args, **kwargs):
        self.exceptions = tuple(re.compile(url) for url in LOGIN_NOT_REQUIRED)
        self.get_response = get_response

        return super(LoginRequiredMiddleware, self).__init__(get_response, *args, **kwargs)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Caso o user ja esteja logado:
        if request.user.is_authenticated:
            if request.user.is_superuser:
                Usuario.objects.get_or_create(user=request.user, defaults={'tipo': 'ADMIN'})
            if re.match(r'/canteirojato/romaneio/pdf/', request.path):
                return None
            for url in self.exceptions:
                if url.match(request.path):
                    return redirect('core:index')
            return None

        for url in self.exceptions:
            if url.match(request.path):
                return None

        return redirect('core:login')
    

