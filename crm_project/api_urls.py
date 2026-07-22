from django.urls import include, path

urlpatterns = [
    path('accounts/', include('accounts.urls')),
    path('public/', include('crm.public_urls')),    # anonymous: contact/lead form
    path('crm/', include('crm.urls')),              # internal staff (IsAgencyStaff)
    path('portal/', include('crm.portal_urls')),    # client portal (IsPortalClient)
    path('marketing/', include('marketing.urls')),
]