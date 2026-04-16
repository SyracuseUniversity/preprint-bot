"""
Add paper deduplication support:
- sha256 field on Paper (unique, nullable)
- corpora M2M field (auto junction table)
- arxiv_id loses unique constraint (sha256 is the dedup key now)
- corpus FK becomes nullable (kept for pipeline backward compat)
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_profile_top_x_default_and_ci_name"),
    ]

    operations = [
        # 1. Add sha256 field (nullable for now; unique added after data migration)
        migrations.AddField(
            model_name="paper",
            name="sha256",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),

        # 2. Make corpus FK nullable (was CASCADE, now SET_NULL for pipeline compat)
        migrations.AlterField(
            model_name="paper",
            name="corpus",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="papers_legacy",
                to="core.corpus",
            ),
        ),

        # 3. Remove unique constraint on arxiv_id
        migrations.AlterField(
            model_name="paper",
            name="arxiv_id",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),

        # 4. Add corpora M2M (Django auto-creates the junction table)
        migrations.AddField(
            model_name="paper",
            name="corpora",
            field=models.ManyToManyField(
                blank=True,
                related_name="papers",
                to="core.corpus",
            ),
        ),

        # 5. Add indexes on arxiv_id and submitted_date
        migrations.AddIndex(
            model_name="paper",
            index=models.Index(fields=["arxiv_id"], name="papers_arxiv_id_idx"),
        ),
        migrations.AddIndex(
            model_name="paper",
            index=models.Index(fields=["submitted_date"], name="papers_submitted_date_idx"),
        ),
    ]
