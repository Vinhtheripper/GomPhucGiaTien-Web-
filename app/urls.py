from django.contrib import admin
from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('cart/', views.cart, name='cart'),
    path('shop/', views.shop, name='shop'),
    path('checkout/', views.checkout, name='checkout'),
    path('service/', views.service, name='service'),
    path('blog/', views.blog, name='blog'),
    path('contactus/', views.contactus, name='contactus'),
    path('prodetail/', views.pro_detail, name='prodetail'),
    path('search/', views.search, name='search'),
    path('confirmpayment/', views.confirmpayment, name='confirmpayment'),
    path('login/', views.loginPage, name='login'),
    path('logout/', views.logoutPage, name='logout'),
    path("register/", views.register, name="register"),
]



