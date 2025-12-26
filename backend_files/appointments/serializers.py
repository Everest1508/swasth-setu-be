from rest_framework import serializers
from .models import Doctor, Appointment
from django.contrib.auth import get_user_model

User = get_user_model()


class DoctorSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    id = serializers.IntegerField(source='pk', read_only=True)
    
    class Meta:
        model = Doctor
        fields = ('id', 'name', 'email', 'specialty', 'experience', 'fee', 
                  'rating', 'reviews_count', 'bio', 'available')

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_email(self, obj):
        return obj.user.email


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    doctor_specialty = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    doctor_id = serializers.IntegerField(source='doctor.id', read_only=True)

    class Meta:
        model = Appointment
        fields = ('id', 'doctor', 'doctor_id', 'doctor_name', 'doctor_specialty', 
                  'patient_name', 'appointment_type', 'status', 'scheduled_date', 
                  'scheduled_time', 'reason', 'notes', 'created_at', 'updated_at')
        read_only_fields = ('id', 'patient', 'created_at', 'updated_at')

    def get_doctor_name(self, obj):
        return obj.doctor.user.get_full_name() or obj.doctor.user.username

    def get_doctor_specialty(self, obj):
        return obj.doctor.specialty

    def get_patient_name(self, obj):
        return obj.patient.get_full_name() or obj.patient.username


class AppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ('doctor', 'appointment_type', 'scheduled_date', 'scheduled_time', 'reason')

    def validate(self, attrs):
        # Check if doctor is available
        if not attrs['doctor'].available:
            raise serializers.ValidationError("Doctor is not available")
        return attrs

