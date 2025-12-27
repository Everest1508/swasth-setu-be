from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, logout
from django.db.models import Q
from django.core.paginator import Paginator
from api.models import User
from appointments.models import Doctor
from pharmacy.models import Pharmacist
from .models import DoctorApplication, PharmacistApplication


def landing_page(request):
    """Landing page view for Swasth Setu - Rural Health Connect"""
    context = {
        'app_name': 'Swasth Setu',
        'tagline': 'Connecting Rural Communities to Healthcare',
    }
    return render(request, 'landing.html', context)


def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and user.is_staff


def user_login(request):
    """Simple login page for users to apply"""
    if request.user.is_authenticated:
        # Check where they came from
        next_url = request.GET.get('next', '/')
        return redirect(next_url)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next', request.GET.get('next', '/'))
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    context = {
        'next': request.GET.get('next', '/'),
    }
    return render(request, 'login.html', context)


def user_logout(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('landing')


def user_register(request):
    """Registration page for new users"""
    if request.user.is_authenticated:
        messages.info(request, 'You are already logged in.')
        return redirect('landing')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        phone = request.POST.get('phone', '')
        location = request.POST.get('location', '')
        
        # Validation
        if not username or not email or not password:
            messages.error(request, 'Username, email, and password are required.')
        elif password != password_confirm:
            messages.error(request, 'Passwords do not match.')
        elif len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters long.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists. Please choose a different one.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered. Please use a different email or login.')
        else:
            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    location=location,
                    is_doctor=False,
                    is_pharmacist=False,
                )
                messages.success(request, 'Registration successful! Please login to continue.')
                return redirect('user_login')
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
    
    return render(request, 'register.html')


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard to manage users, doctors, and pharmacists"""
    # Get statistics
    total_users = User.objects.count()
    total_doctors = Doctor.objects.count()
    total_pharmacists = Pharmacist.objects.count()
    pending_doctor_apps = DoctorApplication.objects.filter(status='pending').count()
    pending_pharmacist_apps = PharmacistApplication.objects.filter(status='pending').count()
    
    context = {
        'total_users': total_users,
        'total_doctors': total_doctors,
        'total_pharmacists': total_pharmacists,
        'pending_doctor_apps': pending_doctor_apps,
        'pending_pharmacist_apps': pending_pharmacist_apps,
    }
    return render(request, 'admin/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def manage_users(request):
    """Manage all users"""
    search = request.GET.get('search', '')
    users = User.objects.all()
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    paginator = Paginator(users, 20)
    page = request.GET.get('page', 1)
    users_page = paginator.get_page(page)
    
    context = {
        'users': users_page,
        'search': search,
    }
    return render(request, 'admin/users.html', context)


@login_required
@user_passes_test(is_admin)
def manage_doctors(request):
    """Manage all doctors"""
    search = request.GET.get('search', '')
    doctors = Doctor.objects.select_related('user').all()
    
    if search:
        doctors = doctors.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(specialty__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    
    paginator = Paginator(doctors, 20)
    page = request.GET.get('page', 1)
    doctors_page = paginator.get_page(page)
    
    context = {
        'doctors': doctors_page,
        'search': search,
    }
    return render(request, 'admin/doctors.html', context)


@login_required
@user_passes_test(is_admin)
def manage_pharmacists(request):
    """Manage all pharmacists"""
    search = request.GET.get('search', '')
    pharmacists = Pharmacist.objects.select_related('user').all()
    
    if search:
        pharmacists = pharmacists.filter(
            Q(user__username__icontains=search) |
            Q(store_name__icontains=search) |
            Q(store_address__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    paginator = Paginator(pharmacists, 20)
    page = request.GET.get('page', 1)
    pharmacists_page = paginator.get_page(page)
    
    context = {
        'pharmacists': pharmacists_page,
        'search': search,
    }
    return render(request, 'admin/pharmacists.html', context)


@login_required
@user_passes_test(is_admin)
def toggle_user_status(request, user_id):
    """Toggle user active status"""
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    messages.success(request, f"User {user.username} status updated.")
    return redirect('admin_manage_users')


@login_required
@user_passes_test(is_admin)
def toggle_doctor_status(request, doctor_id):
    """Toggle doctor availability"""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    doctor.available = not doctor.available
    doctor.save()
    messages.success(request, f"Doctor {doctor.name} availability updated.")
    return redirect('admin_manage_doctors')


@login_required
@user_passes_test(is_admin)
def toggle_pharmacist_status(request, pharmacist_id):
    """Toggle pharmacist active status"""
    pharmacist = get_object_or_404(Pharmacist, id=pharmacist_id)
    pharmacist.is_active = not pharmacist.is_active
    pharmacist.save()
    messages.success(request, f"Pharmacist {pharmacist.store_name} status updated.")
    return redirect('admin_manage_pharmacists')


# Application views
@login_required(login_url='/login/')
def apply_doctor(request):
    """Application form for doctors"""
    if request.method == 'POST':
        # Check if user already has a doctor profile
        if hasattr(request.user, 'doctor_profile'):
            messages.info(request, 'You already have a doctor profile.')
            return redirect('admin_apply_doctor')
        
        # Check for pending application
        if DoctorApplication.objects.filter(user=request.user, status='pending').exists():
            messages.info(request, 'You already have a pending application.')
            return redirect('admin_apply_doctor')
        
        application = DoctorApplication.objects.create(
            user=request.user,
            specialty=request.POST.get('specialty'),
            experience=int(request.POST.get('experience', 0)),
            fee=float(request.POST.get('fee', 0)),
            bio=request.POST.get('bio', ''),
            qualification=request.POST.get('qualification', ''),
            license_number=request.POST.get('license_number', ''),
            clinic_address=request.POST.get('clinic_address', ''),
            phone=request.POST.get('phone', ''),
        )
        messages.success(request, 'Your application has been submitted successfully!')
        return redirect('admin_apply_doctor')
    
    return render(request, 'apply/doctor.html')


@login_required(login_url='/login/')
def apply_pharmacist(request):
    """Application form for pharmacists"""
    if request.method == 'POST':
        # Check if user already has a pharmacist profile
        if hasattr(request.user, 'pharmacist_profile'):
            messages.info(request, 'You already have a pharmacist profile.')
            return redirect('admin_apply_pharmacist')
        
        # Check for pending application
        if PharmacistApplication.objects.filter(user=request.user, status='pending').exists():
            messages.info(request, 'You already have a pending application.')
            return redirect('admin_apply_pharmacist')
        
        application = PharmacistApplication.objects.create(
            user=request.user,
            store_name=request.POST.get('store_name'),
            store_address=request.POST.get('store_address'),
            phone=request.POST.get('phone', ''),
            email=request.POST.get('email', ''),
            license_number=request.POST.get('license_number', ''),
            qualification=request.POST.get('qualification', ''),
        )
        messages.success(request, 'Your application has been submitted successfully!')
        return redirect('admin_apply_pharmacist')
    
    return render(request, 'apply/pharmacist.html')


@login_required
@user_passes_test(is_admin)
def doctor_applications(request):
    """View and manage doctor applications"""
    status_filter = request.GET.get('status', 'all')
    applications = DoctorApplication.objects.select_related('user').all()
    
    if status_filter != 'all':
        applications = applications.filter(status=status_filter)
    
    paginator = Paginator(applications, 20)
    page = request.GET.get('page', 1)
    applications_page = paginator.get_page(page)
    
    context = {
        'applications': applications_page,
        'status_filter': status_filter,
    }
    return render(request, 'admin/doctor_applications.html', context)


@login_required
@user_passes_test(is_admin)
def pharmacist_applications(request):
    """View and manage pharmacist applications"""
    status_filter = request.GET.get('status', 'all')
    applications = PharmacistApplication.objects.select_related('user').all()
    
    if status_filter != 'all':
        applications = applications.filter(status=status_filter)
    
    paginator = Paginator(applications, 20)
    page = request.GET.get('page', 1)
    applications_page = paginator.get_page(page)
    
    context = {
        'applications': applications_page,
        'status_filter': status_filter,
    }
    return render(request, 'admin/pharmacist_applications.html', context)


@login_required
@user_passes_test(is_admin)
def approve_doctor_application(request, app_id):
    """Approve a doctor application"""
    application = get_object_or_404(DoctorApplication, id=app_id)
    
    if application.status != 'pending':
        messages.error(request, 'This application has already been processed.')
        return redirect('admin_doctor_applications')
    
    # Create doctor profile
    doctor = Doctor.objects.create(
        user=application.user,
        specialty=application.specialty,
        experience=application.experience,
        fee=application.fee,
        bio=application.bio,
        clinic_address=application.clinic_address,
    )
    
    # Update user flags
    application.user.is_doctor = True
    application.user.save()
    
    # Update application status
    application.status = 'approved'
    application.save()
    
    messages.success(request, f'Doctor application approved. Doctor profile created for {doctor.name}.')
    return redirect('admin_doctor_applications')


@login_required
@user_passes_test(is_admin)
def approve_pharmacist_application(request, app_id):
    """Approve a pharmacist application"""
    application = get_object_or_404(PharmacistApplication, id=app_id)
    
    if application.status != 'pending':
        messages.error(request, 'This application has already been processed.')
        return redirect('admin_pharmacist_applications')
    
    # Create pharmacist profile
    pharmacist = Pharmacist.objects.create(
        user=application.user,
        store_name=application.store_name,
        store_address=application.store_address,
        phone=application.phone,
        email=application.email,
    )
    
    # Update user flags
    application.user.is_pharmacist = True
    application.user.save()
    
    # Update application status
    application.status = 'approved'
    application.save()
    
    messages.success(request, f'Pharmacist application approved. Pharmacist profile created for {pharmacist.store_name}.')
    return redirect('admin_pharmacist_applications')


@login_required
@user_passes_test(is_admin)
def reject_application(request, app_type, app_id):
    """Reject a doctor or pharmacist application"""
    if app_type == 'doctor':
        application = get_object_or_404(DoctorApplication, id=app_id)
        redirect_url = 'admin_doctor_applications'
    elif app_type == 'pharmacist':
        application = get_object_or_404(PharmacistApplication, id=app_id)
        redirect_url = 'admin_pharmacist_applications'
    else:
        messages.error(request, 'Invalid application type.')
        return redirect('admin_dashboard')
    
    if application.status != 'pending':
        messages.error(request, 'This application has already been processed.')
        return redirect(redirect_url)
    
    if request.method == 'POST':
        application.status = 'rejected'
        application.notes = request.POST.get('notes', '')
        application.save()
        messages.success(request, 'Application rejected.')
        return redirect(redirect_url)
    
    context = {
        'application': application,
        'app_type': app_type,
    }
    return render(request, 'admin/reject_application.html', context)
