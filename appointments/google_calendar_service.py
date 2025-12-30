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
from google.auth.exceptions import RefreshError
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
                    try:
                        creds.refresh(Request())
                    except RefreshError as e:
                        # Refresh token is invalid - user needs to re-authenticate
                        logger.warning(f"Google refresh token is invalid. Re-authentication required: {str(e)}")
                        # Optionally delete the invalid token file to force re-authentication
                        if token_path and os.path.exists(token_path):
                            try:
                                os.remove(token_path)
                                logger.info(f"Removed invalid token file: {token_path}")
                            except Exception as delete_error:
                                logger.warning(f"Could not remove invalid token file: {str(delete_error)}")
                        logger.info("Please run the authentication script to re-authenticate: python authenticate_google_calendar.py")
                        return None
                else:
                    logger.warning("Google credentials not valid. Please authenticate first.")
                    return None
            
            # Build the service
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("Google Calendar service initialized successfully")
            
        except RefreshError as e:
            # Handle refresh token errors specifically
            error_str = str(e)
            if 'invalid_grant' in error_str.lower():
                logger.warning("Google Calendar refresh token is invalid or expired. Re-authentication required.")
                logger.info("To fix this, run: python authenticate_google_calendar.py")
            else:
                logger.error(f"Error refreshing Google Calendar credentials: {error_str}")
            self.service = None
        except Exception as e:
            error_str = str(e)
            logger.error(f"Error initializing Google Calendar service: {error_str}")
            if 'invalid_grant' in error_str.lower():
                logger.info("The Google OAuth token has expired. Please re-authenticate by running: python authenticate_google_calendar.py")
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
                             f'Join the meeting directly using the Google Meet link in this calendar event. '
                             f'You can join up to 15 minutes before the scheduled time. '
                             f'Make sure you are signed in with the email address that received this invitation.',
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
                'guestsCanInviteOthers': True,  # Allow sharing the meeting link with others
                'guestsCanModify': False,  # Prevent guests from modifying
                'guestsCanSeeOtherGuests': True,  # Allow seeing other attendees
                'visibility': 'public',  # Make event visible (helps with open access)
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
                sendUpdates='all'  # Send invitations to all attendees - this ensures they can join directly
            ).execute()
            
            # Extract Meet link
            meet_link = None
            if 'conferenceData' in created_event:
                meet_link = created_event['conferenceData'].get('entryPoints', [{}])[0].get('uri')
            
            # Get organizer email for logging/instructions
            organizer_email = created_event.get('organizer', {}).get('email', 'Unknown')
            
            logger.info(f"Calendar event created for appointment {appointment.id}: {created_event.get('id')}")
            logger.info(f"Organizer: {organizer_email}")
            logger.info(f"Both patient and doctor are invited and can join directly from their calendar invites")
            
            # Configure meeting to be "open to all" - allow anyone with the link to join
            try:
                # Get the current event to update
                event_id = created_event.get('id')
                existing_event = self.service.events().get(
                    calendarId='primary',
                    eventId=event_id
                ).execute()
                
                # Ensure conferenceData is preserved
                if 'conferenceData' not in existing_event or not existing_event.get('conferenceData'):
                    existing_event['conferenceData'] = created_event.get('conferenceData', {})
                
                # Configure for open access - allow guests to invite others
                existing_event['guestsCanInviteOthers'] = True
                existing_event['guestsCanSeeOtherGuests'] = True
                
                # Update event to make it open
                updated_event = self.service.events().patch(
                    calendarId='primary',
                    eventId=event_id,
                    body=existing_event,
                    sendUpdates='none'  # Don't send another update
                ).execute()
                
                # Update meet_link if it changed
                if 'conferenceData' in updated_event:
                    updated_meet_link = updated_event['conferenceData'].get('entryPoints', [{}])[0].get('uri')
                    if updated_meet_link:
                        meet_link = updated_meet_link
                
                logger.info(f"Event configured for open access - anyone with the link can join")
            except Exception as update_error:
                # Log but don't fail - the event was created successfully
                logger.warning(f"Could not update event for open access (non-critical): {str(update_error)}")
            
            # Important note about Quick Access for open meetings
            logger.info(
                f"Meeting created with open access. The meeting link can be shared with anyone. "
                f"To ensure direct joining without 'ask to join', the organizer ({organizer_email}) "
                f"should enable 'Quick Access' in Google Meet settings at meet.google.com"
            )
            
            return {
                'event_id': created_event.get('id'),
                'meet_link': meet_link,
                'html_link': created_event.get('htmlLink'),
                'organizer_email': organizer_email,
                'quick_access_note': (
                    f"To allow direct joining without 'ask to join', the organizer ({organizer_email}) "
                    f"must enable 'Quick Access' in Google Meet settings at meet.google.com"
                )
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


def get_organizer_email():
    """
    Get the email address of the authenticated Google account (organizer).
    This is the account that needs to have 'Quick Access' enabled in Google Meet settings.
    """
    try:
        calendar_service = get_calendar_service()
        if not calendar_service or not calendar_service.service:
            return None
        
        # Get calendar metadata to find organizer email
        calendar = calendar_service.service.calendars().get(calendarId='primary').execute()
        return calendar.get('id')  # This is the email address of the calendar owner
        
    except Exception as e:
        logger.error(f"Error getting organizer email: {str(e)}")
        return None

