from rest_framework import serializers
from .models import Doctor, Appointment, DoctorSchedule, HealthRecord
from django.contrib.auth import get_user_model

User = get_user_model()


class DoctorSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    id = serializers.IntegerField(source='pk', read_only=True)
    
    class Meta:
        model = Doctor
        fields = ('id', 'name', 'email', 'specialty', 'experience', 'fee', 
                  'rating', 'reviews_count', 'bio', 'available', 'clinic_address',
                  'latitude', 'longitude')

    def validate_latitude(self, value):
        """Round latitude to 6 decimal places"""
        if value is not None:
            return round(float(value), 6)
        return value

    def validate_longitude(self, value):
        """Round longitude to 6 decimal places"""
        if value is not None:
            return round(float(value), 6)
        return value

    def update(self, instance, validated_data):
        # Ensure coordinates are rounded
        if 'latitude' in validated_data and validated_data['latitude'] is not None:
            validated_data['latitude'] = round(float(validated_data['latitude']), 6)
        if 'longitude' in validated_data and validated_data['longitude'] is not None:
            validated_data['longitude'] = round(float(validated_data['longitude']), 6)
        return super().update(instance, validated_data)

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_email(self, obj):
        return obj.user.email


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    doctor_specialty = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    doctor_id = serializers.IntegerField(source='doctor.id', read_only=True)
    health_records = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = ('id', 'doctor', 'doctor_id', 'doctor_name', 'doctor_specialty', 
                  'patient_name', 'appointment_type', 'status', 'scheduled_date', 
                  'scheduled_time', 'reason', 'notes', 'prescription', 'google_meet_link', 
                  'health_records', 'created_at', 'updated_at')
        read_only_fields = ('id', 'patient', 'google_meet_link', 'created_at', 'updated_at')

    def get_doctor_name(self, obj):
        return obj.doctor.user.get_full_name() or obj.doctor.user.username

    def get_doctor_specialty(self, obj):
        return obj.doctor.specialty

    def get_patient_name(self, obj):
        return obj.patient.get_full_name() or obj.patient.username
    
    def get_health_records(self, obj):
        """Get health records associated with this appointment"""
        records = obj.health_records.all()[:10]  # Limit to 10 most recent
        return HealthRecordSerializer(records, many=True).data
    
    def get_health_records(self, obj):
        """Get health records associated with this appointment"""
        records = obj.health_records.all()[:10]  # Limit to 10 most recent
        return HealthRecordSerializer(records, many=True).data


class DoctorScheduleSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = DoctorSchedule
        fields = ('id', 'day_of_week', 'day_name', 'start_time', 'end_time', 'is_available')


class AppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ('doctor', 'appointment_type', 'scheduled_date', 'scheduled_time', 'reason')

    def validate(self, attrs):
        from datetime import datetime, timedelta
        
        doctor = attrs['doctor']
        scheduled_date = attrs['scheduled_date']
        scheduled_time = attrs['scheduled_time']
        
        # Check if doctor is available
        if not doctor.available:
            raise serializers.ValidationError("Doctor is not available")
        
        # Check if appointment is in the past
        appointment_datetime = datetime.combine(scheduled_date, scheduled_time)
        if appointment_datetime < datetime.now():
            raise serializers.ValidationError("Cannot book appointments in the past")
        
        # Check doctor's schedule for that day
        day_of_week = scheduled_date.weekday()
        schedule = DoctorSchedule.objects.filter(
            doctor=doctor,
            day_of_week=day_of_week,
            is_available=True
        ).first()
        
        if not schedule:
            raise serializers.ValidationError(
                f"Doctor is not available on {scheduled_date.strftime('%A')}"
            )
        
        # Check if time is within doctor's schedule
        if scheduled_time < schedule.start_time or scheduled_time >= schedule.end_time:
            raise serializers.ValidationError(
                f"Appointment time must be between {schedule.start_time.strftime('%H:%M')} "
                f"and {schedule.end_time.strftime('%H:%M')}"
            )
        
        # Check for overlapping appointments
        # Create a temporary appointment instance to check overlap
        temp_appointment = Appointment(
            doctor=doctor,
            patient=self.context['request'].user,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            status='scheduled'
        )
        
        if temp_appointment.check_overlap():
            raise serializers.ValidationError(
                "This time slot conflicts with an existing appointment. Please choose another time."
            )
        
        return attrs


class AppointmentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating appointments with validation"""
    class Meta:
        model = Appointment
        fields = ('scheduled_date', 'scheduled_time', 'status', 'reason', 'notes', 'prescription')
        extra_kwargs = {
            'scheduled_date': {'required': False},
            'scheduled_time': {'required': False},
            'status': {'required': False},
            'reason': {'required': False},
            'notes': {'required': False},
            'prescription': {'required': False},
        }

    def validate(self, attrs):
        from datetime import datetime
        
        instance = self.instance
        scheduled_date = attrs.get('scheduled_date', instance.scheduled_date)
        scheduled_time = attrs.get('scheduled_time', instance.scheduled_time)
        doctor = instance.doctor
        
        # Only validate if date or time is being changed
        if 'scheduled_date' in attrs or 'scheduled_time' in attrs:
            # Check if doctor is available
            if not doctor.available:
                raise serializers.ValidationError("Doctor is not available")
            
            # Check if appointment is in the past
            appointment_datetime = datetime.combine(scheduled_date, scheduled_time)
            if appointment_datetime < datetime.now():
                raise serializers.ValidationError("Cannot reschedule appointments to the past")
            
            # Check doctor's schedule for that day
            day_of_week = scheduled_date.weekday()
            schedule = DoctorSchedule.objects.filter(
                doctor=doctor,
                day_of_week=day_of_week,
                is_available=True
            ).first()
            
            if not schedule:
                raise serializers.ValidationError(
                    f"Doctor is not available on {scheduled_date.strftime('%A')}"
                )
            
            # Check if time is within doctor's schedule
            if scheduled_time < schedule.start_time or scheduled_time >= schedule.end_time:
                raise serializers.ValidationError(
                    f"Appointment time must be between {schedule.start_time.strftime('%H:%M')} "
                    f"and {schedule.end_time.strftime('%H:%M')}"
                )
            
            # Check for overlapping appointments (excluding current appointment)
            temp_appointment = Appointment(
                id=instance.id,  # Include ID so it's excluded from overlap check
                doctor=doctor,
                patient=instance.patient,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                status=instance.status
            )
            
            if temp_appointment.check_overlap():
                raise serializers.ValidationError(
                    "This time slot conflicts with an existing appointment. Please choose another time."
                )
        
        return attrs


class HealthRecordSerializer(serializers.ModelSerializer):
    """Serializer for health records"""
    created_by_name = serializers.SerializerMethodField()
    appointment_id = serializers.IntegerField(source='appointment.id', read_only=True, allow_null=True)
    attachment_url = serializers.SerializerMethodField()
    
    class Meta:
        model = HealthRecord
        fields = ('id', 'patient', 'appointment', 'appointment_id', 'date', 'title', 
                  'description', 'attachment', 'attachment_url', 'created_by', 'created_by_name', 
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None
    
    def get_attachment_url(self, obj):
        if obj.attachment:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.attachment.url)
            return obj.attachment.url
        return None


class HealthRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating health records"""
    class Meta:
        model = HealthRecord
        fields = ('appointment', 'date', 'title', 'description', 'attachment')
    
    def validate(self, attrs):
        # If appointment is provided, ensure the patient matches
        appointment = attrs.get('appointment')
        if appointment:
            patient = self.context['request'].user
            # For doctors, use the appointment's patient
            if patient.is_doctor:
                attrs['patient'] = appointment.patient
            else:
                # For patients, ensure they can only create records for themselves
                if appointment.patient != patient:
                    raise serializers.ValidationError(
                        "You can only create health records for your own appointments"
                    )
                attrs['patient'] = patient
        else:
            # If no appointment, patient is the current user
            attrs['patient'] = self.context['request'].user
        
        # Set created_by
        attrs['created_by'] = self.context['request'].user
        
        return attrs

