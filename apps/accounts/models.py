from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100, db_index=True)
    last_name = models.CharField(max_length=100, db_index=True)
    phone = models.CharField(max_length=20, blank=True, default="")
    loyalty_points_balance = models.IntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        indexes = [
            models.Index(fields=["email", "is_active"]),
            models.Index(fields=["last_name", "first_name"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def add_loyalty_points(self, points: int, description: str = ""):
        from apps.loyalty.models import LoyaltyTransaction
        self.loyalty_points_balance += points
        self.save(update_fields=["loyalty_points_balance"])
        
        LoyaltyTransaction.objects.create(
            user=self,
            points=points,
            transaction_type=LoyaltyTransaction.TransactionType.CREDIT,
            description=description,
        )

    def deduct_loyalty_points(self, points: int, description: str = ""):
        if self.loyalty_points_balance < points:
            raise ValueError("Insufficient points")
        
        from apps.loyalty.models import LoyaltyTransaction
        self.loyalty_points_balance -= points
        self.save(update_fields=["loyalty_points_balance"])
        
        LoyaltyTransaction.objects.create(
            user=self,
            points=points,
            transaction_type=LoyaltyTransaction.TransactionType.DEBIT,
            description=description,
        )
