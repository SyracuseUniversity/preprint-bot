from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_pbuser_email_verified"),
    ]

    operations = [
        migrations.AddField(
            model_name="pbuser",
            name="orcid_id",
            field=models.CharField(
                blank=True, max_length=19, null=True, unique=True,
            ),
        ),
    ]
