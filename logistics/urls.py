from django.conf.urls import include, url
from django.contrib import admin
from . import settings
from django.contrib.auth import views as auth_views
from rest_framework_jwt.views import obtain_jwt_token

admin.autodiscover()

#import hello.views

urlpatterns = [
    #url(r'^$', hello.views.index, name='index'),
    url(r'^docs/', include('rest_framework_docs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^gauth/', include('gauth.urls')),
    #url(r'^graphs/', include('graphs.urls')),
    url(r'^ics/', include('ics.urls')),
    url(r'^qr/', include('qr.urls')),
    url(r'^api-token-auth/', obtain_jwt_token),
    url(r'^auth/', include('rest_auth.urls'))
    #url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    #url(r'^dashboard/', include('dashboard.urls')),
]

urlpatterns += [url(r'^silk/', include('silk.urls', namespace='silk'))]

# if settings.DEBUG:
#   import debug_toolbar
#   urlpatterns = [
#     url(r'^__debug__/', include(debug_toolbar.urls)),
#   ] + urlpatterns
