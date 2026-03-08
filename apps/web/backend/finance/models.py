from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone 

class UserProfile(models.Model):
    """
    Unified Profile Model.
    Field names (monthlyIncome, etc.) match your React state exactly 
    to avoid mapping logic in the frontend.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Financial Goals (Matching React keys)
    monthlyIncome = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    monthlyBudget = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    dailyBudget = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    # Meta Data
    is_business = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user.username}"

class Transaction(models.Model):
    TRANSACTION_TYPES = (('income', 'Income'), ('expense', 'Expense'))
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, default='expense')
    category = models.CharField(max_length=100, default='other')
    date = models.DateField(default=timezone.now)
    is_recurring = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.title} - {self.amount}"

class WealthItem(models.Model):
    # Mapping to your React "type": "asset" or "liability"
    TYPE_CHOICES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wealth_items")
    title = models.CharField(max_length=100)  # e.g., "HDFC Bank", "Car Loan"
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    category = models.CharField(max_length=50, default="General") # e.g., "Cash", "Investment"
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.amount}"
    
class TaxProfile(models.Model):
    # Link to the built-in Django User
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='tax_profile')
    
    # Checkbox field
    is_business = models.BooleanField(default=False)
    
    # Numeric Input fields (from your 'fields' constant in React)
    annual_rent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    annual_epf = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    nps_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    health_insurance_self = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    health_insurance_parents = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    home_loan_interest = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    education_loan_interest = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Metadata
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Tax Profile for {self.user.username}"
    
class ITRData(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="itr_profile")
    
    # Stores: salary, houseProperty, businessIncome, capitalGains, otherIncome, interestIncome
    income_data = models.JSONField(default=dict, blank=True)
    
    # Stores: section80C, section80D, section80E, section80G, hra, homeLoanInterest, nps80CCD
    deductions_data = models.JSONField(default=dict, blank=True)
    
    # Stores: panNumber, aadharNumber, bankAccount, ifscCode, email, mobile
    filing_details = models.JSONField(default=dict, blank=True)
    
    # Tracks the user's choice: 'new' or 'old'
    tax_regime = models.CharField(max_length=10, default="new", choices=[('new', 'New'), ('old', 'Old')])
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ITR Data"
        verbose_name_plural = "ITR Data Profiles"

    def __str__(self):
        return f"ITR Profile: {self.user.username} ({self.tax_regime.upper()})"
   

class ApiAuditLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="api_audit_logs",
    )
    request_id = models.CharField(max_length=64, db_index=True)
    action = models.CharField(max_length=64)
    resource_type = models.CharField(max_length=64)
    resource_id = models.CharField(max_length=64, blank=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=255)
    status_code = models.IntegerField()
    error_code = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action}:{self.status_code}:{self.request_id}"
