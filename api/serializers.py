from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 
                  'first_name', 'last_name', 'phone', 'location')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        # Prevent doctor registration through public API
        if attrs.get('is_doctor', False):
            raise serializers.ValidationError({
                "is_doctor": "Doctors cannot register through this endpoint. Please contact admin."
            })
        # Prevent pharmacist registration through public API
        if attrs.get('is_pharmacist', False):
            raise serializers.ValidationError({
                "is_pharmacist": "Pharmacists cannot register through this endpoint. Please contact admin."
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        # Ensure is_doctor and is_pharmacist are always False for public registration
        validated_data['is_doctor'] = False
        validated_data['is_pharmacist'] = False
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                  'full_name', 'phone', 'location', 'is_doctor', 'is_pharmacist', 'date_joined')
        read_only_fields = ('id', 'is_doctor', 'is_pharmacist', 'date_joined')


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone', 'location')


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['is_doctor'] = user.is_doctor
        token['is_pharmacist'] = user.is_pharmacist
        token['full_name'] = user.full_name
        return token

