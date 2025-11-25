from django.db import models
from accounts.models import User

MENU_STATUS_CHOICES = [
    ("idle", "Idle"),
    ("pending", "Pending"),
    ("processing", "Processing"),
    ("succeeded", "Succeeded"),
    ("failed", "Failed"),
]


class Restaurant(models.Model):
    owner = models.OneToOneField(User,null=True, blank=True,on_delete=models.SET_NULL,related_name='owned_restaurants')      
    name = models.CharField(max_length=255)
    menu_pdf = models.FileField(upload_to="restaurant_menus/", null=True, blank=True)
    address = models.TextField(blank=True,null=True)
    phone = models.CharField(max_length=20)
    # email = models.EmailField()
    logo = models.ImageField(upload_to='restaurant_logos/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)   

    menu_json = models.FileField(upload_to="restaurant_menus/json/", null=True, blank=True)
    menu_extract_status = models.CharField(max_length=12, choices=MENU_STATUS_CHOICES, default="idle")
    menu_last_extracted_at = models.DateTimeField(null=True, blank=True)
    menu_extract_error = models.TextField(blank=True, default="")    
    

    def __str__(self):
        return self.name
    
    

    class Meta:
        ordering = ['name']


