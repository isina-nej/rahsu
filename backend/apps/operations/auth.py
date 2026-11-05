"""Cookie/session authentication with explicit CSRF and constrained signup."""
import os
from django.contrib.auth import authenticate,login,logout,get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView


class AuthThrottle(SimpleRateThrottle):
    scope='auth'
    def get_cache_key(self,request,view):
        return self.cache_format % {'scope':self.scope,'ident':self.get_ident(request)}


class CsrfView(APIView):
    permission_classes=[AllowAny]
    authentication_classes=[]
    def get(self,request):
        return Response({'csrfToken':get_token(request._request)})


class AuthStatusView(APIView):
    permission_classes=[AllowAny]
    def get(self,request):
        user=request.user
        return Response({'authenticated':user.is_authenticated,
            'username':user.get_username() if user.is_authenticated else '',
            'staff':bool(user.is_authenticated and user.is_staff),
            'signup_enabled':os.getenv('ALLOW_PUBLIC_SIGNUP')=='1'})


class CredentialsSerializer(serializers.Serializer):
    username=serializers.CharField(min_length=3,max_length=50)
    password=serializers.CharField(min_length=8,max_length=200,write_only=True)


@method_decorator(csrf_protect,name='dispatch')
class LoginView(APIView):
    permission_classes=[AllowAny]
    authentication_classes=[]
    throttle_classes=[AuthThrottle]

    def post(self,request):
        ser=CredentialsSerializer(data=request.data);ser.is_valid(raise_exception=True)
        user=authenticate(request._request,username=ser.validated_data['username'],
                          password=ser.validated_data['password'])
        if user is None or not user.is_active:
            return Response({'error':'invalid_credentials'},status=400)
        login(request._request,user)
        return Response({'authenticated':True,'username':user.get_username()})


@method_decorator(csrf_protect,name='dispatch')
class LogoutView(APIView):
    permission_classes=[IsAuthenticated]
    throttle_classes=[AuthThrottle]

    def post(self,request):
        logout(request._request)
        return Response({'authenticated':False})


@method_decorator(csrf_protect,name='dispatch')
class RegisterView(APIView):
    permission_classes=[AllowAny]
    authentication_classes=[]
    throttle_classes=[AuthThrottle]

    def post(self,request):
        if os.getenv('ALLOW_PUBLIC_SIGNUP')!='1':
            return Response({'error':'registration_closed'},status=403)
        ser=CredentialsSerializer(data=request.data);ser.is_valid(raise_exception=True)
        data=ser.validated_data
        User=get_user_model()
        if User.objects.filter(username=data['username']).exists():
            return Response({'error':'username_unavailable'},status=400)
        try:
            validate_password(data['password'])
        except ValidationError as exc:
            return Response({'error':'weak_password','details':exc.messages},status=400)
        user=User.objects.create_user(username=data['username'],password=data['password'])
        login(request._request,user)
        return Response({'authenticated':True,'username':user.get_username()},status=201)
