"""
Google Calendar and Google Meet Integration Service

This service handles:
- Creating Google Calendar events for video appointments
- Generating Google Meet links
- Sending calendar invitations to patients and doctors
"""

from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/calendar.events']


class GoogleCalendarService:
    """Service for Google Calendar and Google Meet integration"""
    
    def __init__(self):
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Calendar API service"""
        try:
            # Check if credentials file exists
            credentials_path = getattr(settings, 'GOOGLE_CREDENTIALS_PATH', None)
            token_path = getattr(settings, 'GOOGLE_TOKEN_PATH', None)
            
            # Convert Path objects to strings if needed
            if credentials_path:
                credentials_path = str(credentials_path)
            if token_path:
                token_path = str(token_path)
            
            if not credentials_path or not os.path.exists(credentials_path):
                logger.warning("Google credentials not configured. Calendar integration disabled.")
                return None
            
            # Load credentials
            creds = None
            if token_path and os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            # If there are no (valid) credentials available, return None
            # User needs to authenticate first
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    logger.warning("Google credentials not valid. Please authenticate first.")
                    return None
            
            # Build the service
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("Google Calendar service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Google Calendar service: {str(e)}")
            self.service = None
    
    def create_calendar_event(self, appointment):
        """
        Create a Google Calendar event with Google Meet link for an appointment
        
        Args:
            appointment: Appointment instance
            
        Returns:
            dict: Contains 'event_id' and 'meet_link' if successful, None otherwise
        """
        if not self.service:
            logger.warning("Google Calendar service not available")
            return None
        
        if appointment.appointment_type != 'video':
            logger.info("Skipping calendar event creation for non-video appointment")
            return None
        
        try:
            # Combine date and time for the event (naive datetime - local time)
            event_datetime = datetime.combine(
                appointment.scheduled_date,
                appointment.scheduled_time
            )
            
            # Event end time (30 minutes duration)
            event_end_datetime = event_datetime + timedelta(minutes=30)
            
            # Format for Google Calendar API (use local time, specify timezone)
            # Use Asia/Kolkata for India, or adjust based on your location
            # Google Calendar expects timezone in IANA format (e.g., 'Asia/Kolkata', 'America/New_York')
            timezone_str = 'Asia/Kolkata'  # Change this to your actual timezone
            
            # Format datetime strings (local time, will be interpreted in the specified timezone)
            start_time = event_datetime.strftime('%Y-%m-%dT%H:%M:%S')
            end_time = event_end_datetime.strftime('%Y-%m-%dT%H:%M:%S')
            
            # Event details
            patient_name = appointment.patient.get_full_name() or appointment.patient.username
            doctor_name = appointment.doctor.user.get_full_name() or appointment.doctor.user.username
            
            event = {
                'summary': f'Video Consultation: {patient_name} with Dr. {doctor_name}',
                'description': f'Video consultation appointment.\n\n'
                             f'Patient: {patient_name}\n'
                             f'Doctor: {doctor_name}\n'
                             f'Specialty: {appointment.doctor.specialty}\n'
                             f'Reason: {appointment.reason or "Not specified"}\n\n'
                             f'Please join the meeting using the Google Meet link.',
                'start': {
                    'dateTime': start_time,
                    'timeZone': timezone_str,
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': timezone_str,
                },
                'attendees': [
                    {'email': appointment.patient.email},
                    {'email': appointment.doctor.user.email},
                ],
                'conferenceData': {
                    'createRequest': {
                        'requestId': f'appointment-{appointment.id}-{datetime.now().timestamp()}',
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        }
                    }
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 15},  # 15 minutes before
                    ],
                },
            }
            
            # Create the event
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,
                sendUpdates='all'  # Send invitations to all attendees
            ).execute()
            
            # Extract Meet link
            meet_link = None
            if 'conferenceData' in created_event:
                meet_link = created_event['conferenceData'].get('entryPoints', [{}])[0].get('uri')
            
            logger.info(f"Calendar event created for appointment {appointment.id}: {created_event.get('id')}")
            
            return {
                'event_id': created_event.get('id'),
                'meet_link': meet_link,
                'html_link': created_event.get('htmlLink'),
            }
            
        except HttpError as e:
            logger.error(f"Error creating Google Calendar event: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating calendar event: {str(e)}")
            return None
    
    def update_calendar_event(self, appointment):
        """
        Update an existing Google Calendar event
        
        Args:
            appointment: Appointment instance with google_calendar_event_id
            
        Returns:
            dict: Updated event info or None
        """
        if not self.service or not appointment.google_calendar_event_id:
            return None
        
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId='primary',
                eventId=appointment.google_calendar_event_id
            ).execute()
            
            # Update event details (use same timezone as create method)
            event_datetime = datetime.combine(
                appointment.scheduled_date,
                appointment.scheduled_time
            )
            event_end_datetime = event_datetime + timedelta(minutes=30)
            
            timezone_str = 'Asia/Kolkata'  # Must match the timezone used in create_calendar_event
            start_time = event_datetime.strftime('%Y-%m-%dT%H:%M:%S')
            end_time = event_end_datetime.strftime('%Y-%m-%dT%H:%M:%S')
            
            event['start'] = {
                'dateTime': start_time,
                'timeZone': timezone_str,
            }
            event['end'] = {
                'dateTime': end_time,
                'timeZone': timezone_str,
            }
            
            # Update event
            updated_event = self.service.events().update(
                calendarId='primary',
                eventId=appointment.google_calendar_event_id,
                body=event,
                sendUpdates='all'
            ).execute()
            
            logger.info(f"Calendar event updated for appointment {appointment.id}")
            return {
                'event_id': updated_event.get('id'),
                'meet_link': updated_event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri') if 'conferenceData' in updated_event else None,
            }
            
        except HttpError as e:
            logger.error(f"Error updating Google Calendar event: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error updating calendar event: {str(e)}")
            return None
    
    def delete_calendar_event(self, appointment):
        """
        Delete a Google Calendar event
        
        Args:
            appointment: Appointment instance with google_calendar_event_id
        """
        if not self.service or not appointment.google_calendar_event_id:
            return False
        
        try:
            self.service.events().delete(
                calendarId='primary',
                eventId=appointment.google_calendar_event_id,
                sendUpdates='all'
            ).execute()
            
            logger.info(f"Calendar event deleted for appointment {appointment.id}")
            return True
            
        except HttpError as e:
            logger.error(f"Error deleting Google Calendar event: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting calendar event: {str(e)}")
            return False


# Singleton instance
_calendar_service = None

def get_calendar_service():
    """Get or create Google Calendar service instance"""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = GoogleCalendarService()
    return _calendar_service

