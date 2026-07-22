from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
	use_in_migrations = True

	def _create_user(self, email, password, **extra_fields):
		if not email:
			raise ValueError('The email field must be set')

		email = self.normalize_email(email)
		user = self.model(email=email, **extra_fields)
		user.set_password(password)
		user.save(using=self._db)
		return user

	def create_user(self, email, password=None, **extra_fields):
		extra_fields.setdefault('is_staff', False)
		extra_fields.setdefault('is_superuser', False)
		return self._create_user(email, password, **extra_fields)

	def create_superuser(self, email, password=None, **extra_fields):
		extra_fields.setdefault('is_staff', True)
		extra_fields.setdefault('is_superuser', True)

		if extra_fields.get('is_staff') is not True:
			raise ValueError('Superuser must have is_staff=True.')
		if extra_fields.get('is_superuser') is not True:
			raise ValueError('Superuser must have is_superuser=True.')

		return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
	class Role(models.TextChoices):
		CLIENT = 'client', 'Client'
		EMPLOYEE = 'employee', 'Employee'
		ADMIN = 'admin', 'Admin'

	email = models.EmailField(unique=True)
	first_name = models.CharField(max_length=150, blank=True)
	last_name = models.CharField(max_length=150, blank=True)
	role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)
	is_staff = models.BooleanField(default=False)
	is_active = models.BooleanField(default=True)
	date_joined = models.DateTimeField(auto_now_add=True)

	objects = UserManager()

	USERNAME_FIELD = 'email'
	REQUIRED_FIELDS = []

	class Meta:
		verbose_name = 'user'
		verbose_name_plural = 'users'

	def __str__(self):
		return self.email


class ClientProfile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
	company_name = models.CharField(max_length=255, blank=True)
	industry = models.CharField(max_length=255, blank=True)
	billing_address = models.TextField(blank=True)

	def __str__(self):
		return self.company_name or self.user.email


class EmployeeProfile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
	department = models.CharField(max_length=255, blank=True)
	hire_date = models.DateField(null=True, blank=True)

	def __str__(self):
		return self.department or self.user.email
