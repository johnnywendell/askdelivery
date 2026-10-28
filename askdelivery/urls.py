"""
URL configuration for askdelivery project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from .settings import DEBUG, MEDIA_ROOT, MEDIA_URL
from django.conf import settings
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('api/tracking/', include('tracking.urls')),
    path('wallet/', include('wallet.urls')),
    path('orders/', include('orders.urls')),
    path(
        'service-worker.js',
        TemplateView.as_view(
            template_name='pwa/service-worker.js',
            content_type='application/javascript'
        ),
        name='service-worker'
    )
]

if DEBUG:
    urlpatterns += static(
        MEDIA_URL,
        document_root=MEDIA_ROOT
    )