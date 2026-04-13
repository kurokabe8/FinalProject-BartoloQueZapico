from django.db import models

class Employee(models.Model):
    name = models.CharField(max_length=255)
    id_number = models.CharField(max_length=100, unique=True) 
    rate = models.FloatField()
    overtime_pay = models.FloatField(null=True, blank=True, default=0) 
    allowance = model.FloatField(null=True, blank=True, default=0) 

    def getName(self):
        return self.name
    
    def getID(self):
        return self.id_number
    
    def getRate(self):
        return self.rate
    
    def getOvertime(self):
        return self.overtime_pay
    
    def getAllowance(self):
        return self.allowance
    
    def __str__(self):
        return f"pk: {self.id_number}, rate: {self.rate}"
