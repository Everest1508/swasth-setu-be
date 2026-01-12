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
    username_field = 'username'  # Default field
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow email or username for login - make username optional
        self.fields['email'] = serializers.EmailField(required=False, allow_blank=True)
        # Make username not required if email is provided
        if 'username' in self.fields:
            self.fields['username'].required = False
            self.fields['username'].allow_blank = True
    
    def validate(self, attrs):
        # Check if email is provided instead of username
        email = attrs.get('email', '').strip()
        username = attrs.get('username', '').strip()
        
        # If email is provided but username is not, find user by email
        if email and not username:
            try:
                user = User.objects.get(email=email)
                attrs['username'] = user.username
            except User.DoesNotExist:
                raise serializers.ValidationError({
                    'email': 'No user found with this email address.'
                })
        elif not email and not username:
            # Neither email nor username provided
            raise serializers.ValidationError({
                'username': 'Username or email is required.',
                'email': 'Username or email is required.'
            })
        
        # Remove email from attrs as it's not needed for token generation
        attrs.pop('email', None)
        
        # Ensure username is present after processing
        if not attrs.get('username'):
            raise serializers.ValidationError({
                'username': 'Username is required.',
                'email': 'Email is required.'
            })
        
        return super().validate(attrs)
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['is_doctor'] = user.is_doctor
        token['is_pharmacist'] = user.is_pharmacist
        token['full_name'] = user.full_name
        return token

