from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_pbuser_orcid_id"),
    ]

    operations = [
        # Change top_x default from 10 to 999
        migrations.AlterField(
            model_name="profile",
            name="top_x",
            field=models.IntegerField(default=999),
        ),
        # Replace unique_together with explicit constraints
        migrations.AlterUniqueTogether(
            name="profile",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="profile",
            constraint=models.UniqueConstraint(
                fields=["user", "name"],
                name="profiles_user_name_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="profile",
            constraint=models.UniqueConstraint(
                Lower("name"),
                "user",
                name="profiles_user_name_ci_unique",
            ),
        ),
    ]
