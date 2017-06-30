from __future__ import unicode_literals

from django.db import models


# Create your models here.
# maps to signup_word in the DB
class Word(models.Model):
    word = models.CharField(max_length=60)
    frequency = models.IntegerField()


# maps to signup_student in the DB
class Student(models.Model):
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    access_token = models.CharField(max_length=64, unique=True)


class CrawlerURL(models.Model):
    url = models.URLField(unique=True)
    visited = models.BooleanField(default=False)