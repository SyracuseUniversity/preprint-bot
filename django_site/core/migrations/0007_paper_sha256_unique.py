"""
Add unique constraint on sha256 after data migration has populated values
and deduplicated rows.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_populate_paper_hashes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paper",
            name="sha256",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
    ]
